import pandas as pd
import re
import streamlit as st
from io import StringIO
from itertools import combinations

# ----------------- UI 설정 -----------------
st.set_page_config(page_title="💘 조건 우선 정렬 매칭기", layout="wide")

st.markdown("""
    <style>
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        .stTextArea textarea {
            background-color: #fdf6fa;
            font-family: 'Arial';
            font-size: 14px;
        }
        .stDataFrame {
            font-size: 13px;
        }
        .big-button .stButton>button {
            font-size: 16px;
            height: 3em;
            width: 100%;
            background-color: #ffdef0;
            color: black;
            border-radius: 10px;
        }
    </style>
""", unsafe_allow_html=True)

st.title("💘 조건 우선 정렬 매칭기")
st.subheader("🌈 레이디 이어주기 매칭 분석기")
st.caption("TSV 전체 붙여넣기 후 ➡️ **[🔍 분석 시작]** 버튼을 눌러주세요")

# ----------------- 입력 -----------------
st.markdown("#### 📥 TSV 데이터를 아래에 붙여넣어 주세요:")
raw_text = st.text_area("TSV 데이터", height=300, label_visibility="collapsed")
run = st.button("🔍 분석 시작", help="붙여넣기 후 눌러주세요")

st.markdown("---")

# ----------------- helpers -----------------
SEP = re.compile(r"[,/]|\s+")

def tokens(val):
    return [t.strip() for t in SEP.split(str(val)) if t.strip()]

def ranges_overlap(val1, val2):
    def parse_ranges(val):
        if not val or pd.isna(val):
            return []
        parts = [v.strip() for v in str(val).split(",") if v.strip()]
        ranges = []
        for part in parts:
            part = part.replace("세 이상", "~100").replace("세이상", "~100")
            part = part.replace("세 이하", "0~").replace("세이하", "0~")
            part = re.sub(r"[^\d~]", "", part)
            if "~" in part:
                try:
                    s, e = part.split("~")
                    s = float(s or 0)
                    e = float(e or 100)
                    ranges.append((s, e))
                except:
                    continue
            else:
                try:
                    v = float(part)
                    ranges.append((v, v))
                except:
                    continue
        return ranges

    r1 = parse_ranges(val1)
    r2 = parse_ranges(val2)

    for s1, e1 in r1:
        for s2, e2 in r2:
            if max(s1, s2) <= min(e1, e2):
                return True
    return False

def clean_column(col: str) -> str:
    return re.sub(r"\s+", " ", col).strip().replace("\n", "")

def find_column(df, keyword: str):
    return next((c for c in df.columns if keyword in c), None)

def distance_match(a_self, a_pref, b_self, b_pref):
    a_tokens = tokens(a_pref)
    b_tokens = tokens(b_pref)
    if "단거리" in a_tokens or "단거리" in b_tokens:
        return a_self.strip() == b_self.strip()
    return True

# ----------------- main -----------------
if run and raw_text:
    try:
        df = pd.read_csv(StringIO(raw_text), sep="\t", dtype=str, engine="python")
        df.columns = [clean_column(c) for c in df.columns]

        # 자동 컬럼 탐색
        NICK = find_column(df, "닉네임")
        MUST = find_column(df, "꼭 맞아야")
        DIST_SELF = find_column(df, "거주 지역")
        DIST_PREF = find_column(df, "거리 조건")
        AGE_SELF = find_column(df, "레이디 나이")
        AGE_PREF = find_column(df, "선호하는 상대방 레이디 나이")
        HEIGHT_SELF = find_column(df, "레이디 키")
        HEIGHT_PREF = find_column(df, "상대방 레이디 키")

        if not all([NICK, MUST, DIST_SELF, DIST_PREF, AGE_SELF, AGE_PREF]):
            st.error("❌ 필수 컬럼이 누락되었습니다.")
            st.write("컬럼 목록:", df.columns.tolist())
            st.stop()

        condition_fields = {
            "나이": (AGE_SELF, AGE_PREF),
            "키": (HEIGHT_SELF, HEIGHT_PREF),
            "거리": (DIST_SELF, DIST_PREF),
            "흡연": (find_column(df, "흡연(레이디)"), find_column(df, "흡연(상대방 레이디)")),
            "음주": (find_column(df, "음주(레이디)"), find_column(df, "음주(상대방 레이디)")),
            "타투": (find_column(df, "타투(레이디)"), find_column(df, "타투(상대방 레이디)")),
            "벽장": (find_column(df, "벽장(레이디)"), find_column(df, "벽장(상대방 레이디)")),
            "성격": (find_column(df, "성격(레이디)"), find_column(df, "성격(상대방 레이디)")),
            "연락 텀": (find_column(df, "연락 텀(레이디)"), find_column(df, "연락 텀(상대방 레이디)")),
            "머리 길이": (find_column(df, "머리 길이(레이디)"), find_column(df, "머리 길이(상대방 레이디)")),
            "데이트 주기": (find_column(df, "데이트 선호 주기"), find_column(df, "데이트 선호 주기")),
        }

        df = df[df[NICK].notna()].drop_duplicates(subset=[NICK]).reset_index(drop=True)

        results = []
        for i, j in combinations(df.index, 2):
            A, B = df.loc[i], df.loc[j]
            a_nick, b_nick = A[NICK].strip(), B[NICK].strip()
            if not a_nick or not b_nick:
                continue

            musts = list(set(tokens(A[MUST])) | set(tokens(B[MUST])))
            must_total = len(musts)
            must_matched = 0
            reasons = []

            for key in musts:
                if key not in condition_fields or not all(condition_fields[key]):
                    continue
                a_field, b_field = condition_fields[key]
                a_self = A.get(a_field, "")
                a_pref = A.get(b_field, "")
                b_self = B.get(a_field, "")
                b_pref = B.get(b_field, "")

                if key in ["나이", "키"]:
                    ok1 = ranges_overlap(a_self, b_pref)
                    ok2 = ranges_overlap(b_self, a_pref)
                    if ok1 and ok2:
                        must_matched += 1
                    else:
                        reasons.append(f"{key} 불일치")
                elif a_field == b_field:
                    if str(A[a_field]).strip() == str(B[b_field]).strip():
                        must_matched += 1
                    else:
                        reasons.append(f"{key} 불일치")
                else:
                    if set(tokens(A[a_field])).intersection(tokens(B[b_field])) and \
                       set(tokens(B[a_field])).intersection(tokens(A[b_field])):
                        must_matched += 1
                    else:
                        reasons.append(f"{key} 불일치")

            match_rate = round((must_matched / must_total * 100) if must_total else 0.0, 1)

            # 나이 일치
            age_match = "✅" if ranges_overlap(A[AGE_SELF], B[AGE_PREF]) and ranges_overlap(B[AGE_SELF], A[AGE_PREF]) else "❌"
            if age_match == "❌":
                reasons.append("나이 조건 불일치")

            # 거리 일치
            real_dist_match = distance_match(A[DIST_SELF], A[DIST_PREF], B[DIST_SELF], B[DIST_PREF])
            dist_match = "✅" if real_dist_match else "❌"
            if "거리" in musts and not real_dist_match:
                reasons.append("거리 조건 불일치 (단거리 요구 & 지역 다름)")

            results.append({
                "A ↔ B": f"{a_nick} ↔ {b_nick}",
                "필수 조건 일치율 (%)": match_rate,
                "나이 일치": age_match,
                "거리 일치": dist_match,
                "나이 일치 점수": 1 if age_match == "✅" else 0,
                "거리 일치 점수": 1 if ("거리" in musts and real_dist_match) else 0,
                "나이 동일 여부": 1 if A[AGE_SELF] == B[AGE_SELF] else 0,
                "지역 동일 여부": 1 if A[DIST_SELF] == B[DIST_SELF] else 0,
                "불일치 이유": "\n".join(reasons) if reasons else "",
                "필수 조건 개수": must_total,
                "일치한 필수 조건 수": must_matched
            })

        out = pd.DataFrame(results)
        out = out.sort_values(
            by=[
                "필수 조건 일치율 (%)",
                "나이 일치 점수",
                "거리 일치 점수",
                "나이 동일 여부",
                "지역 동일 여부"
            ],
            ascending=[False, False, False, False, False]
        ).reset_index(drop=True)

        if out.empty:
            st.warning("😢 매칭 결과가 없습니다.")
        else:
            st.success(f"✅ 총 {len(out)}쌍 비교 완료! 조건 정렬 결과가 아래에 표시됩니다.")
            st.dataframe(out.drop(columns=[
                "나이 일치 점수", "거리 일치 점수", "나이 동일 여부", "지역 동일 여부"
            ]), use_container_width=True)

            st.download_button(
                label="📥 매칭 결과 CSV 다운로드",
                data=out.to_csv(index=False).encode("utf-8-sig"),
                file_name="매칭_결과.csv",
                mime="text/csv"
            )

    except Exception as e:
        st.error(f"❌ 분석 실패: {e}")
else:
    st.info("👆 TSV 붙여넣고 ➡️ **[🔍 분석 시작]** 버튼을 눌러주세요")
