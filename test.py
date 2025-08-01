import pandas as pd
import re
import streamlit as st
from io import StringIO
from itertools import permutations
import base64

# ----------------- UI -----------------
st.set_page_config(page_title="💘 필수 조건 매칭기 (불일치 이유까지)", layout="wide")
st.title("🌈 레이디 이어주기 매칭 분석기 (불일치 이유 포함)")
st.caption("TSV 전체 붙여넣기 후 ➡️ **[🔍 분석 시작]** 버튼을 눌러주세요")

raw_text = st.text_area("📥 TSV 데이터를 붙여넣기", height=300)
run = st.button("🔍 분석 시작")
st.markdown("---")

# ----------------- helper -----------------
SEP = re.compile(r"[,/]|\s+")

def tokens(val):
    return [t.strip() for t in SEP.split(str(val)) if t.strip()]

def numeric_match(value, rng):
    try:
        v = float(value)
    except:
        return False
    rng = str(rng).replace("이상", "0~").replace("이하", "~1000").replace(" ", "")
    if "~" in rng:
        s, e = rng.split("~"); s = float(s or 0); e = float(e or 1000)
        return s <= v <= e
    try:
        return v == float(rng)
    except:
        return False

def clean_column(col: str) -> str:
    return col.replace("\n", " ").replace("\r", " ").replace('"', '').strip()

# ----------------- main -----------------
if run and raw_text:
    try:
        df = pd.read_csv(StringIO(raw_text), sep="\t", dtype=str, engine="python")
        df.columns = [clean_column(c) for c in df.columns]

        NICK = "닉네임"
        MUST = "꼭 맞아야 하는 조건들은 무엇인가레?"
        DIST_SELF = "레이디의 거주 지역"
        DIST_PREF = "희망하는 거리 조건"
        AGE_SELF = "레이디 나이"
        AGE_PREF = "선호하는 상대방 레이디 나이"
        HEIGHT_SELF = "레이디 키"
        HEIGHT_PREF = "상대방 레이디 키"

        if NICK not in df.columns or MUST not in df.columns:
            st.error("❌ 필수 컬럼이 없습니다. (닉네임 / 꼭 맞아야 하는 조건들은 무엇인가레?)")
            st.stop()

        condition_fields = {
            "나이": (AGE_SELF, AGE_PREF),
            "키": (HEIGHT_SELF, HEIGHT_PREF),
            "거리": (DIST_SELF, DIST_PREF),
            "흡연": ("[흡연(레이디)]", "[흡연(상대방 레이디)]"),
            "음주": ("[음주(레이디)]", "[음주(상대방 레이디) ]"),
            "타투": ("[타투(레이디)]", "[타투(상대방 레이디)]"),
            "벽장": ("[벽장(레이디)]", "[벽장(상대방 레이디)]"),
            "성격": ("[성격(레이디)]", "[성격(상대방 레이디)]"),
            "연락 텀": ("[연락 텀(레이디)]", "[연락 텀(상대방 레이디)]"),
            "머리 길이": ("[머리 길이(레이디)]", "[머리 길이(상대방 레이디)]"),
            "데이트 주기": ("[데이트 선호 주기]", "[데이트 선호 주기]"),
        }

        df = df[df[NICK].notna()].drop_duplicates(subset=[NICK]).reset_index(drop=True)

        results = []
        for i, j in permutations(df.index, 2):
            A, B = df.loc[i], df.loc[j]
            a_nick, b_nick = A[NICK].strip(), B[NICK].strip()
            if not a_nick or not b_nick:
                continue

            musts = list(set(tokens(A[MUST]) + ["나이", "거리"]))
            all_match = True
            matched_items = []
            unmatched_reasons = []

            for key in musts:
                if key not in condition_fields:
                    continue
                a_field, b_field = condition_fields[key]

                a_val_self = A.get(a_field, "")
                a_val_pref = A.get(b_field, "")
                b_val_self = B.get(a_field, "")
                b_val_pref = B.get(b_field, "")

                if key == "나이":
                    ok1 = numeric_match(a_val_self, b_val_pref)
                    ok2 = numeric_match(b_val_self, a_val_pref)
                    if ok1 and ok2:
                        matched_items.append(f"나이: {a_nick}({a_val_self}) ⬄ {b_nick}({b_val_self}) ✅")
                    else:
                        unmatched_reasons.append("나이 조건 불일치")
                        all_match = False

                elif key == "키":
                    ok1 = numeric_match(a_val_self, b_val_pref)
                    ok2 = numeric_match(b_val_self, a_val_pref)
                    if ok1 and ok2:
                        matched_items.append(f"키: {a_nick}({a_val_self}) ⬄ {b_nick}({b_val_self}) ✅")
                    else:
                        unmatched_reasons.append("키 조건 불일치")
                        all_match = False

                elif key == "거리":
                    if "단거리" in str(A[DIST_PREF]) or "단거리" in str(B[DIST_PREF]):
                        if A[DIST_SELF] == B[DIST_SELF]:
                            matched_items.append(f"지역: {A[DIST_SELF]} ⬄ {B[DIST_SELF]}, 단거리 조건 → ✅")
                        else:
                            unmatched_reasons.append(f"거리 조건 불일치 (단거리 요구 & 지역 다름)")
                            all_match = False
                    else:
                        matched_items.append(f"지역: {A[DIST_SELF]} ⬄ {B[DIST_SELF]}, 거리 무관 → ✅")

                elif a_field == b_field:
                    if str(A[a_field]).strip() == str(B[b_field]).strip():
                        matched_items.append(f"{key}: 동일 → ✅")
                    else:
                        unmatched_reasons.append(f"{key} 불일치")
                        all_match = False

                else:
                    t1 = set(tokens(A[a_field])).intersection(tokens(B[b_field]))
                    t2 = set(tokens(B[a_field])).intersection(tokens(A[b_field]))
                    if t1 and t2:
                        matched_items.append(f"{key}: 양방향 일부 일치 → ✅")
                    else:
                        unmatched_reasons.append(f"{key} 불일치")
                        all_match = False

            results.append({
                "A": a_nick,
                "B": b_nick,
                "결과": "✅" if all_match else "❌",
                "일치 조건 설명": "\n".join(matched_items),
                "불일치 이유": "\n".join(unmatched_reasons),
                "필수 조건": ", ".join(musts)
            })

        out = pd.DataFrame(results)
        if out.empty:
            st.warning("😢 매칭 결과가 없습니다.")
        else:
            st.success(f"총 {len(out)}쌍 분석 완료 (일치 + 불일치 포함)")
            st.dataframe(out, use_container_width=True)
            st.download_button("📥 CSV 다운로드", out.to_csv(index=False).encode("utf-8-sig"), "매칭_결과_전체.csv", "text/csv")

    except Exception as e:
        st.error(f"❌ 분석 실패: {e}")
else:
    st.info("TSV 붙여넣고 ➡️ 분석 시작!")
