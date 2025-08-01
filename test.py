import pandas as pd
import re
import streamlit as st
from io import StringIO
from itertools import permutations

# ----------------- UI -----------------
st.set_page_config(page_title="💘 조건 우선 정렬 매칭기", layout="wide")
st.title("🌈 레이디 이어주기 매칭 분석기 (우선순위 정렬 + 사유 출력)")
st.caption("TSV 전체 붙여넣기 후 ➡️ **[🔍 분석 시작]** 버튼을 눌러주세요")

raw_text = st.text_area("📥 TSV 데이터를 붙여넣기", height=300)
run = st.button("🔍 분석 시작")
st.markdown("---")

# ----------------- helper -----------------
SEP = re.compile(r"[,/]|\s+")

def tokens(val):
    return [t.strip() for t in SEP.split(str(val)) if t.strip()]

def numeric_match(value, range_expr):
    try:
        v = float(re.sub(r"[^\d.]", "", str(value)))  # 숫자만 추출
    except:
        return False

    if not range_expr or pd.isna(range_expr):
        return False

    parts = [r.strip() for r in str(range_expr).split(",") if r.strip()]

    for rng in parts:
        rng = rng.replace("세 이상", "~100").replace("세이상", "~100")
        rng = rng.replace("세 이하", "0~").replace("세이하", "0~")
        rng = re.sub(r"[^\d~]", "", rng)

        if "~" in rng:
            try:
                s, e = rng.split("~")
                s = float(s or 0)
                e = float(e or 100)
                if s <= v <= e:
                    return True
            except:
                continue
        else:
            try:
                if v == float(rng):
                    return True
            except:
                continue

    return False

def clean_column(col: str) -> str:
    return re.sub(r"\s+", " ", col).strip().replace("\n", "")

# ----------------- main -----------------
if run and raw_text:
    try:
        df = pd.read_csv(StringIO(raw_text), sep="\t", dtype=str, engine="python")
        df.columns = [clean_column(c) for c in df.columns]

        # ✅ 컬럼명 수동 지정
        NICK = "오늘 레개팅에서 쓰실 닉네임은 무엇인가레?  (오픈카톡 닉네임과 동(성)일 하게이 맞춰주she레즈)"
        MUST = "꼭 맞아야 하는 조건들은 무엇인가레? (레개팅에서 가장 우선적으로 반영되는 기준입레다. 반드she 맞아야 하는 중요한 조건만 신중히 선택해 주she레즈.)"
        DIST_SELF = "레이디의 거주 지역"
        DIST_PREF = "희망하는 거리 조건 (범위 안내 - 단거리 : 동일 지역 안, 장거리 : 동일 지역 외 포함)"
        AGE_SELF = "레이디 나이"
        AGE_PREF = "선호하는 상대방 레이디 나이"
        HEIGHT_SELF = "레이디 키를 적어주she레즈 (숫자만 적어주세여자)"
        HEIGHT_PREF = "상대방 레이디 키를  적어주she레즈  (예시 : 154~, ~170)"

        # ✅ 조건 매핑
        condition_fields = {
            "나이": (AGE_SELF, AGE_PREF),
            "키": (HEIGHT_SELF, HEIGHT_PREF),
            "거리": (DIST_SELF, DIST_PREF),
            "흡연": ("세부 조건  Yes or No [흡연(레이디)]", "세부 조건  Yes or No [흡연(상대방 레이디)]"),
            "음주": ("세부 조건  Yes or No [음주(레이디)]", "세부 조건  Yes or No [음주(상대방 레이디) ]"),
            "타투": ("세부 조건  Yes or No [타투(레이디)]", "세부 조건  Yes or No [타투(상대방 레이디)]"),
            "벽장": ("세부 조건  Yes or No [벽장(레이디)]", "세부 조건  Yes or No [벽장(상대방 레이디)]"),
            "성격": ("성격 [성격(레이디)]", "성격 [성격(상대방 레이디)]"),
            "연락 텀": ("긴 or 짧 [연락 텀(레이디)]", "긴 or 짧 [연락 텀(상대방 레이디)]"),
            "머리 길이": ("긴 or 짧 [머리 길이(레이디)]", "긴 or 짧 [머리 길이(상대방 레이디)]"),
            "데이트 주기": ("긴 or 짧 [데이트 선호 주기]", "긴 or 짧 [데이트 선호 주기]"),
        }

        df = df[df[NICK].notna()].drop_duplicates(subset=[NICK]).reset_index(drop=True)

        results = []
        for i, j in permutations(df.index, 2):
            A, B = df.loc[i], df.loc[j]
            a_nick, b_nick = A[NICK].strip(), B[NICK].strip()
            if not a_nick or not b_nick:
                continue

            musts = list(set(tokens(A[MUST])))
            must_total = len(musts)
            must_matched = 0
            reasons = []

            for key in musts:
                if key not in condition_fields:
                    continue
                a_field, b_field = condition_fields[key]
                a_self = A.get(a_field, "")
                a_pref = A.get(b_field, "")
                b_self = B.get(a_field, "")
                b_pref = B.get(b_field, "")

                if key in ["나이", "키"]:
                    ok1 = numeric_match(a_self, b_pref)
                    ok2 = numeric_match(b_self, a_pref)
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

            # 나이 비교
            age_match = "❌"
            if numeric_match(A[AGE_SELF], B[AGE_PREF]) and numeric_match(B[AGE_SELF], A[AGE_PREF]):
                age_match = "✅"
            else:
                reasons.append("나이 조건 불일치")

            # 거리 비교
            dist_match = "무관"
            if "단거리" in str(A[DIST_PREF]) or "단거리" in str(B[DIST_PREF]):
                if A[DIST_SELF] == B[DIST_SELF]:
                    dist_match = "✅"
                else:
                    dist_match = "❌"
                    reasons.append("거리 조건 불일치 (단거리 요구 & 지역 다름)")

            results.append({
                "A": a_nick,
                "B": b_nick,
                "필수 조건 일치율 (%)": match_rate,
                "나이 일치": age_match,
                "거리 일치": dist_match,
                "불일치 이유": "\n".join(reasons) if reasons else "",
                "필수 조건 개수": must_total,
                "일치한 필수 조건 수": must_matched
            })

        out = pd.DataFrame(results)
        out = out.sort_values(
            by=["필수 조건 일치율 (%)", "나이 일치", "거리 일치"],
            ascending=[False, False, False]
        ).reset_index(drop=True)

        if out.empty:
            st.warning("😢 매칭 결과가 없습니다.")
        else:
            st.success(f"총 {len(out)}쌍 비교 완료 (정렬: 일치율 → 나이 → 거리)")
            st.dataframe(out, use_container_width=True)
            st.download_button("📥 CSV 다운로드", out.to_csv(index=False).encode("utf-8-sig"), "매칭_결과.csv", "text/csv")

    except Exception as e:
        st.error(f"❌ 분석 실패: {e}")
else:
    st.info("TSV 붙여넣고 ➡️ 분석 시작!")
