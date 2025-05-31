import pandas as pd
import re
import streamlit as st
from io import StringIO
from itertools import permutations

# ---------- basic page setup ----------
st.set_page_config(page_title="💘 레이디 매칭 분석기 4.0", layout="wide")

st.title("🌈 레이디 이어주기 매칭 분석기 4.0")
st.markdown("붙여넣은 TSV 데이터를 자동으로 정리해 궁합을 계산합니다 ·· ✨")

raw_text = st.text_area("📥 TSV 데이터를 붙여넣기", height=300)
start = st.button("🔍 분석 시작")

# ---------- helpers ----------

def clean_cols(cols: pd.Index) -> pd.Index:
    return (cols.str.replace(r"\s+", " ", regex=True)
                .str.replace("\n", " ")
                .str.strip())

# value matching util
SEP = re.compile(r"[,/]|\s+")

def tokenise(val: str):
    return [t.strip() for t in SEP.split(str(val)) if t.strip()]

def pref_ok(self_val: str, pref_val: str) -> bool:
    if pd.isna(pref_val) or str(pref_val).strip() == "":
        return False
    tokens = tokenise(pref_val)
    if "상관없음" in tokens:
        return True
    return any(tok in tokenise(self_val) for tok in tokens)

# numeric range helpers

def parse_range(txt: str):
    txt = str(txt).strip()
    if txt == "":
        return None, None
    txt = txt.replace("이하", "~1000").replace("이상", "0~")
    if "~" in txt:
        start, end = txt.split("~")
        return float(start or 0), float(end or 1000)
    try:
        v = float(txt)
        return v, v
    except:
        return None, None

def num_ok(num, rng_txt):
    s, e = parse_range(rng_txt)
    if s is None:
        return False
    try:
        num = float(num)
    except:
        return False
    return s <= num <= e

# ---------- main ----------
if start and raw_text:
    try:
        df = pd.read_csv(StringIO(raw_text), sep="\t", engine="python")
        df.columns = clean_cols(df.columns)

        # find nickname column
        nick_candidates = [c for c in df.columns if "닉네임" in c]
        if not nick_candidates:
            st.error("닉네임 컬럼을 찾을 수 없습니다 – 헤더 줄바꿈을 제거하거나 확인해 주세요.")
            st.stop()
        nick_col = nick_candidates[0]
        df = df[df[nick_col].notna() & (df[nick_col].astype(str).str.strip() != "")]  # drop empty nicks
        df = df.drop_duplicates(subset=nick_col)

        # build self/pref column pairs automatically
        self_cols = [c for c in df.columns if "(레이디)" in c and "(상대방" not in c]
        pairs = []
        for self_c in self_cols:
            pref_c = self_c.replace("(레이디)", "(상대방 레이디)")
            if pref_c in df.columns:
                pairs.append((self_c, pref_c))
        # explicit numeric columns
        num_pairs = [("레이디 나이", "선호하는 상대방 레이디 나이"),
                     ("레이디 키를 적어주she레즈 (숫자만 적어주세여자)", "상대방 레이디 키를  적어주she레즈  (예시 : 154~, ~170)")]
        pairs += num_pairs

        # must column name
        must_col = "꼭 맞아야 하는 조건들은 무엇인가레?"
        res_rows = []
        for i, j in permutations(df.index, 2):
            A, B = df.loc[i], df.loc[j]
            a_nick, b_nick = str(A[nick_col]).strip(), str(B[nick_col]).strip()
            if not a_nick or not b_nick:
                continue

            score = 0
            total = 0
            matched_labels = []
            # --- iterate over attribute pairs ---
            for self_c, pref_c in pairs:
                a_self = A.get(self_c, ""); b_self = B.get(self_c, "")
                a_pref = A.get(pref_c, ""); b_pref = B.get(pref_c, "")

                # numeric columns handled separately
                if self_c.startswith("레이디 나이"):
                    cond = num_ok(A[self_c], B[pref_c]) or num_ok(B[self_c], A[pref_c])
                elif self_c.startswith("레이디 키"):
                    cond = num_ok(A[self_c], B[pref_c]) or num_ok(B[self_c], A[pref_c])
                else:
                    cond = pref_ok(a_self, b_pref) or pref_ok(b_self, a_pref)

                # we count only if at least one pref field not empty
                if (str(a_pref).strip() or str(b_pref).strip()):
                    total += 1
                    if cond:
                        score += 1
                        matched_labels.append(self_c.split("[")[0].strip())

            # check must conditions (A 요구 B)
            must_items = tokenise(A.get(must_col, ""))
            must_fail = False
            for m in must_items:
                if m == "거리":
                    if "단거리" in str(A.get("희망하는 거리 조건", "")) and A.get("레이디의 거주 지역") != B.get("레이디의 거주 지역"):
                        must_fail = True; break
                elif m == "성격":
                    if not pref_ok(B.get("성격 [성격(레이디)]", ""), A.get("성격 [성격(상대방 레이디)]", "")):
                        must_fail = True; break
                # add more mappings as needed
            if must_fail:
                score, total = 0, 0
                matched_labels = ["❌ 필수 조건 불일치"]

            percent = round(score/total*100, 1) if total else 0.0
            res_rows.append({"A": a_nick, "B": b_nick, "궁합 점수": f"{score}/{total}", "퍼센트": percent, "일치": ", ".join(matched_labels)})

        res_df = pd.DataFrame(res_rows).sort_values("퍼센트", ascending=False)
        if res_df.empty:
            st.warning("😢 매칭 결과가 없습니다.")
        else:
            st.success(f"{len(res_df)}쌍 매칭 완료 ✨")
            st.dataframe(res_df, use_container_width=True)
            st.download_button("CSV 다운로드", res_df.to_csv(index=False).encode("utf-8-sig"), "lady_match_results.csv", "text/csv")

    except Exception as err:
        st.error(f"❌ 분석 오류: {err}")
else:
    st.info("TSV 데이터를 붙여넣고 버튼을 눌러 분석을 시작하세요!")
