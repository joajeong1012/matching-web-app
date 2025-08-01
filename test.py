import pandas as pd
import re
import streamlit as st
from io import StringIO
from itertools import combinations

# ----------------- UI -----------------
st.set_page_config(page_title="💘 전체 조건 매칭기", layout="wide")
st.title("💘 전체 조건 기반 레이디 매칭기")
st.caption("TSV 전체 붙여넣기 후 ➡️ **[🔍 분석 시작]** 버튼을 눌러주세요")

raw_text = st.text_area("📥 TSV 데이터를 붙여넣기", height=300)
run = st.button("🔍 분석 시작")
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
    a_tokens = set(tokens(a_pref))
    b_tokens = set(tokens(b_pref))
    a_short_only = "단거리" in a_tokens and "장거리" not in a_tokens
    b_short_only = "단거리" in b_tokens and "장거리" not in b_tokens
    if a_short_only or b_short_only:
        return a_self.strip() == b_self.strip()
    return True

# ----------------- main -----------------
if run and raw_text:
    try:
        df = pd.read_csv(StringIO(raw_text), sep="\t", dtype=str, engine="python")
        df.columns = [clean_column(c) for c in df.columns]

        NICK = find_column(df, "닉네임")
        DIST_SELF = find_column(df, "거주 지역")
        DIST_PREF = find_column(df, "거리 조건")
        AGE_SELF = find_column(df, "레이디 나이")
        AGE_PREF = find_column(df, "선호하는 상대방 레이디 나이")
        HEIGHT_SELF = find_column(df, "레이디 키")
        HEIGHT_PREF = find_column(df, "상대방 레이디 키")

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

        all_conditions = [k for k in condition_fields if all(condition_fields[k])]

        results = []
        for i, j in combinations(df.index, 2):
            A, B = df.loc[i], df.loc[j]
            a_nick, b_nick = A[NICK].strip(), B[NICK].strip()
            matched = 0
            issues = []

            for key in all_conditions:
                a_field, b_field = condition_fields[key]
                a_self = str(A.get(a_field, ""))
                a_pref = str(A.get(b_field, ""))
                b_self = str(B.get(a_field, ""))
                b_pref = str(B.get(b_field, ""))

                if key in ["나이", "키"]:
                    ok1 = ranges_overlap(b_self, a_pref)
                    ok2 = ranges_overlap(a_self, b_pref)
                    if ok1 and ok2:
                        matched += 1
                    else:
                        if not ok1:
                            issues.append(f"A의 {key} 조건 불일치")
                        if not ok2:
                            issues.append(f"B의 {key} 조건 불일치")
                elif key == "거리":
                    ok = distance_match(a_self, a_pref, b_self, b_pref)
                    if ok:
                        matched += 1
                    else:
                        issues.append("거리 조건 불일치")
                else:
                    tok_a = set(tokens(a_self))
                    tok_ap = set(tokens(a_pref))
                    tok_b = set(tokens(b_self))
                    tok_bp = set(tokens(b_pref))
                    a_ok = bool(tok_ap & tok_b)
                    b_ok = bool(tok_bp & tok_a)
                    if a_ok and b_ok:
                        matched += 1
                    else:
                        if not a_ok:
                            issues.append(f"A의 {key} 조건 불일치")
                        if not b_ok:
                            issues.append(f"B의 {key} 조건 불일치")

            total = len(all_conditions)
            match_rate = round(matched / total * 100, 1)
            age_ok = ranges_overlap(A[AGE_SELF], B[AGE_PREF]) and ranges_overlap(B[AGE_SELF], A[AGE_PREF])
            dist_ok = distance_match(A[DIST_SELF], A[DIST_PREF], B[DIST_SELF], B[DIST_PREF])

            results.append({
                "A ↔ B": f"{a_nick} ↔ {b_nick}",
                "전체 조건 일치율 (%)": match_rate,
                "나이 일치": "✅" if age_ok else "❌",
                "거리 일치": "✅" if dist_ok else "❌",
                "나이 일치 점수": 1 if age_ok else 0,
                "거리 일치 점수": 1 if dist_ok else 0,
                "불일치 이유": ", ".join(issues) if issues else "",
                "일치한 조건 수": matched,
                "총 조건 수": total,
                "나이 동일 여부": 1 if A[AGE_SELF] == B[AGE_SELF] else 0,
                "지역 동일 여부": 1 if A[DIST_SELF] == B[DIST_SELF] else 0,
            })

        out = pd.DataFrame(results)
        out = out.sort_values(
            by=["전체 조건 일치율 (%)", "나이 일치 점수", "거리 일치 점수", "나이 동일 여부", "지역 동일 여부"],
            ascending=[False, False, False, False, False]
        ).reset_index(drop=True)

        if out.empty:
            st.warning("😢 매칭 결과가 없습니다.")
        else:
            st.success(f"총 {len(out)}쌍 비교 완료!")
            st.dataframe(out.drop(columns=[
                "나이 일치 점수", "거리 일치 점수", "나이 동일 여부", "지역 동일 여부"
            ]), use_container_width=True)
            st.download_button("📥 CSV 다운로드", out.to_csv(index=False).encode("utf-8-sig"), "전체조건_매칭결과.csv", "text/csv")

    except Exception as e:
        st.error(f"❌ 분석 실패: {e}")
else:
    st.info("TSV 붙여넣고 ➡️ 분석 시작!")
