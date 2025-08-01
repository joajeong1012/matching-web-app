import pandas as pd
import re
import streamlit as st
from io import StringIO
from itertools import permutations

# ----------------- UI -----------------
st.set_page_config(page_title="💘 조건 완전일치 매칭기", layout="wide")
st.title("🔍 나이 + 지역 + 필수조건 일치 매칭 분석기")
st.caption("TSV 전체 붙여넣기 후 ➡️ **[🔍 분석 시작]** 버튼을 눌러주세요")

raw_text = st.text_area("📥 TSV 데이터를 붙여넣기", height=250)
run = st.button("🔍 분석 시작")

# ----------------- helpers -----------------
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

# ----------------- main -----------------
if run and raw_text:
    try:
        df = pd.read_csv(StringIO(raw_text), sep="\t", dtype=str, engine="python")
        df.columns = (df.columns.str.replace(r"\s+", " ", regex=True)
                                  .str.replace("\n", " ")
                                  .str.strip())

        # 닉네임 컬럼
        nick_cols = [c for c in df.columns if "닉네임" in c]
        if not nick_cols:
            st.error("❌ 닉네임 컬럼을 찾지 못했습니다.")
            st.stop()
        NICK = nick_cols[0]

        # 필요한 컬럼
        AGE_SELF = "레이디 나이"
        AGE_PREF = "선호하는 상대방 레이디 나이"
        DIST_SELF = "레이디의 거주 지역"
        DIST_PREF = "희망하는 거리 조건"
        MUST_COL = next((c for c in df.columns if "꼭 맞아야" in c), None)

        for col in [AGE_SELF, AGE_PREF, DIST_SELF, DIST_PREF, MUST_COL]:
            if col not in df.columns:
                st.error(f"❌ 누락된 컬럼: {col}")
                st.stop()

        df = (df[df[NICK].notna() & (df[NICK].astype(str).str.strip() != "")]
                .drop_duplicates(subset=[NICK])
                .reset_index(drop=True))

        rows = []
        for i, j in permutations(df.index, 2):
            A, B = df.loc[i], df.loc[j]
            a_nick, b_nick = A[NICK].strip(), B[NICK].strip()
            if not a_nick or not b_nick:
                continue

            # 나이 조건 (양방향)
            age_match = (
                numeric_match(A[AGE_SELF], B[AGE_PREF]) and
                numeric_match(B[AGE_SELF], A[AGE_PREF])
            )

            # 거리 조건
            dist_match = True
            a_dist = A.get(DIST_SELF, "")
            b_dist = B.get(DIST_SELF, "")
            a_pref = A.get(DIST_PREF, "")
            b_pref = B.get(DIST_PREF, "")
            if "단거리" in a_pref or "단거리" in b_pref:
                dist_match = a_dist == b_dist

            # 필수 조건 체크
            must_match = True
            must_tokens = tokens(A[MUST_COL])
            for cond in must_tokens:
                cond = cond.lower()
                if cond == "거리":
                    if "단거리" in a_pref and a_dist != b_dist:
                        must_match = False; break
                elif cond == "성격":
                    a_pref_trait = A.get("성격 [성격(상대방 레이디)]", "")
                    b_self_trait = B.get("성격 [성격(레이디)]", "")
                    if not set(tokens(a_pref_trait)).intersection(tokens(b_self_trait)):
                        must_match = False; break

            if age_match and dist_match and must_match:
                rows.append({
                    "A": a_nick,
                    "B": b_nick,
                    "나이 조건": f"{A[AGE_SELF]} ↔︎ {B[AGE_PREF]}, {B[AGE_SELF]} ↔︎ {A[AGE_PREF]}",
                    "지역": f"{a_dist} - {b_dist}",
                    "필수 조건": ", ".join(must_tokens),
                    "일치": "✅"
                })

        out = pd.DataFrame(rows)
        if out.empty:
            st.warning("😢 나이, 지역, 필수 조건에 모두 일치하는 매칭 결과가 없습니다.")
        else:
            st.success(f"✨ 총 {len(out)}쌍 매칭 완료!")
            st.dataframe(out, use_container_width=True)
            st.download_button("CSV 다운로드", out.to_csv(index=False).encode("utf-8-sig"), "필수조건_매칭결과.csv", "text/csv")

    except Exception as e:
        st.error(f"❌ 분석 실패: {e}")
else:
    st.info("TSV 붙여넣고 ➡️ 분석 시작!")

