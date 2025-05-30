import streamlit as st
import pandas as pd
from io import StringIO
from itertools import permutations

# ---------- UI ----------
st.set_page_config(page_title="레이디 매칭 분석기", layout="wide")
st.markdown("<h1 style='color:#f76c6c;'>💘 레이디 이어주기 매칭 분석기 2.0</h1>", unsafe_allow_html=True)
raw_txt = st.text_area("📥 TSV 응답 전체를 붙여넣으세요", height=300)

# ---------- 매핑 ----------
column_mapping = {
    "오늘 레게팅에서 쓰실 닉네임은 무엇인가레? (오픈카톡 닉네임과 동(성)일 하게이 맞춰주she레즈)": "닉네임",
    "레이디 나이": "레이디 나이",
    "선호하는 상대방 레이디 나이": "선호하는 상대방 레이디 나이",
    "레이디의 거주 지역": "레이디의 거주 지역",
    "희망하는 거리 조건": "희망하는 거리 조건",
}
drop_columns = ["긴 or 짧 [손톱 길이 (농담)]", "34열", "28열", "타임스탬프"]

# ---------- 정제 ----------
def clean_df(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [str(c).replace("\n"," ").replace('"',"").replace("  "," ").strip() for c in df.columns]

    auto = {}
    for c in df.columns:
        if "닉네임" in c:                 auto[c] = "닉네임"
        elif "레이디 키" in c and "상대방" not in c:
                                          auto[c] = "레이디 키"
        elif "레이디 키" in c and "상대방" in c:
                                          auto[c] = "상대방 레이디 키"
        elif "레이디 나이" in c and "상대방" not in c:
                                          auto[c] = "레이디 나이"
        elif "나이" in c and "상대방" in c:
                                          auto[c] = "선호하는 상대방 레이디 나이"
        elif "거주 지역" in c:            auto[c] = "레이디의 거주 지역"
        elif "희망하는 거리 조건" in c:   auto[c] = "희망하는 거리 조건"
    df = df.rename(columns=auto).rename(columns=column_mapping)

    df = df.drop(columns=[c for c in drop_columns if c in df.columns], errors="ignore")
    df = df.loc[:, ~df.columns.duplicated()]
    df = df.fillna("")          # NaN → 빈 문자열
    return df

# ---------- 유틸 ----------
def parse_range(text):
    if pd.isna(text) or str(text).strip() == "":
        return (None, None)
    t = str(text).strip()
    if "~" in t:
        lo, hi = t.replace(" ", "").split("~", 1)
        lo = float(lo) if lo else None
        hi = float(hi) if hi else lo
        return lo, hi
    try:
        f = float(t)
        return f, f
    except ValueError:
        return (None, None)

def is_in_range(value, range_text):
    if pd.isna(value) or pd.isna(range_text) or str(range_text).strip() == "":
        return False
    lo, hi = parse_range(range_text)
    if lo is None: return False
    try:
        v = float(value)
        return lo <= v <= hi
    except (ValueError, TypeError):
        return False

def is_in_range_list(value, range_texts):
    texts = str(range_texts).split(",") if pd.notna(range_texts) else []
    return any(is_in_range(value, t.strip()) for t in texts if t.strip())

def to_list(x):
    return [s.strip() for s in str(x).split(",")] if pd.notna(x) and str(x).strip() else []

def multi_match(a, b):
    A, B = to_list(a), to_list(b)
    return any(x in B for x in A)

def list_overlap(a_list, b_list):
    return multi_match(",".join(a_list), ",".join(b_list))

# ---------- 점수 ----------
def score(a, b):
    s, t = 0, 0
    if is_in_range_list(a["레이디 나이"], b["선호하는 상대방 레이디 나이"]): s+=2
    t+=1
    if is_in_range_list(b["레이디 나이"], a["선호하는 상대방 레이디 나이"]): s+=2
    t+=1
    if is_in_range(a["레이디 키"], b["상대방 레이디 키"]): s+=1
    t+=1
    if is_in_range(b["레이디 키"], a["상대방 레이디 키"]): s+=1
    t+=1
    # 거리
    if "단거리" in a["희망하는 거리 조건"] or "단거리" in b["희망하는 거리 조건"]:
        t+=1
        if a["레이디의 거주 지역"] == b["레이디의 거주 지역"]: s+=1
    else: s+=1; t+=1
    # 성격(예시)  -- 필요한 항목만 넣고 확장 가능
    if multi_match(a.get("성격(레이디)",""), b.get("성격(상대방)","")): s+=1
    if multi_match(b.get("성격(레이디)",""), a.get("성격(상대방)","")): s+=1
    t+=2
    return s, t

# ---------- 매칭 ----------
def build_matches(df):
    if "닉네임" not in df.columns:
        st.error("❌ '닉네임' 컬럼이 없습니다!")
        st.stop()
    seen, out = set(), []
    for i, j in permutations(df.index, 2):
        A, B = df.loc[i], df.loc[j]
        pair = tuple(sorted([A["닉네임"], B["닉네임"]]))
        if pair in seen: continue
        seen.add(pair)
        sc, tot = score(A, B)
        out.append({"A": pair[0], "B": pair[1], "점수": sc, "총": tot, "비율%": round(sc/tot*100,1)})
    return pd.DataFrame(out).sort_values("비율%", ascending=False)

# ---------- 실행 ----------
if raw_txt:
    try:
        raw_df = pd.read_csv(StringIO(raw_txt), sep="\t")
        df = clean_df(raw_df)
        st.success("✅ 정제 완료")
        if df.empty:
            st.warning("⚠ 응답 행이 없습니다. 실제 응답 내용까지 붙여넣어 주세요.")
            st.stop()
        result = build_matches(df)
        st.dataframe(result if not result.empty else "조건 맞는 매칭이 없습니다.")
    except Exception as e:
        st.exception(e)
