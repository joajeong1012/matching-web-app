import streamlit as st
import pandas as pd
from io import StringIO
from itertools import permutations

# ---------- 페이지 ----------
st.set_page_config(page_title="레이디 매칭 분석기", layout="wide")
st.markdown("<h1 style='color:#f76c6c;'>💘 레이디 이어주기 매칭 분석기 2.0</h1>", unsafe_allow_html=True)
st.info("구글폼 TSV 전체 복붙만 하면 자동 분석돼요!")

raw_txt = st.text_area("📥 TSV 응답 붙여넣기", height=300)

# ---------- (선택) 고정 매핑 ----------
column_mapping = {
    "오늘 레게팅에서 쓰실 닉네임은 무엇인가레? (오픈카톡 닉네임과 동(성)일 하게이 맞춰주she레즈)": "닉네임",
    "레이디 나이": "레이디 나이",
    "선호하는 상대방 레이디 나이": "선호하는 상대방 레이디 나이",
    "레이디의 거주 지역": "레이디의 거주 지역",
    "희망하는 거리 조건": "희망하는 거리 조건",
}

drop_columns = ["긴 or 짧 [손톱 길이 (농담)]", "34열", "28열", "타임스탬프"]

# ---------- 정제 ----------
def clean_df(df):
    # 줄바꿈·따옴표·중복 공백 제거
    df.columns = [str(c).replace("\n", " ").replace('"', "").replace("  ", " ").strip()
                  for c in df.columns]

    # 자동 규칙 매핑
    auto = {}
    for c in df.columns:
        if "닉네임" in c:                  auto[c] = "닉네임"
        elif "레이디 키" in c and "상대방" not in c:
                                           auto[c] = "레이디 키"
        elif "레이디 키" in c and "상대방" in c:
                                           auto[c] = "상대방 레이디 키"
        elif "레이디 나이" in c and "상대방" not in c:
                                           auto[c] = "레이디 나이"
        elif "나이" in c and "상대방" in c:
                                           auto[c] = "선호하는 상대방 레이디 나이"
        elif "거주 지역" in c:             auto[c] = "레이디의 거주 지역"
        elif "희망하는 거리 조건" in c:    auto[c] = "희망하는 거리 조건"
    df = df.rename(columns=auto).rename(columns=column_mapping)

    df = df.drop(columns=[c for c in drop_columns if c in df.columns], errors="ignore")
    df = df.loc[:, ~df.columns.duplicated()]
    df = df.fillna("")
    return df

# ---------- 유틸 ----------
def parse_range(t):
    if pd.isna(text) or str(text).strip() == "":
        return (None, None)
    t = str(t).strip()
    if "~" in t:
        a, b = t.replace(" ", "").split("~")
        return float(a), float(b or a)
    return (float(t), float(t))

def is_in_range(v, rng):
    if pd.isna(val) or pd.isna(range_text) or str(range_text).strip() == "":   # ← 추가
        return False
    try:
        lo, hi = parse_range(range_text)
        return lo is not None and lo <= float(val) <= hi
    except ValueError:
        return False   # 잘못된 숫자·빈문자면 False

def is_in_range_list(v, txt):
    lst = str(txt).split(",") if pd.notna(txt) else []
    return any(is_in_range(v, s.strip()) for s in lst if s.strip())

def to_list(x):
    return [s.strip() for s in str(x).split(",")] if pd.notna(x) else []

def multi_match(a, b):
    A, B = to_list(a), to_list(b)
    return any(x in B for x in A)

# ---------- 점수 ----------
def score(a, b):
    s, t, hit = 0, 0, []
    if is_in_range_list(a["레이디 나이"], b["선호하는 상대방 레이디 나이"]): s+=2; hit.append("A나이"); 
    t+=1
    if is_in_range_list(b["레이디 나이"], a["선호하는 상대방 레이디 나이"]): s+=2; hit.append("B나이"); 
    t+=1

    if is_in_range(a["레이디 키"], b["상대방 레이디 키"]): s+=1; hit.append("A키"); 
    t+=1
    if is_in_range(b["레이디 키"], a["상대방 레이디 키"]): s+=1; hit.append("B키"); 
    t+=1

    if "단거리" in a["희망하는 거리 조건"] or "단거리" in b["희망하는 거리 조건"]:
        t+=1
        if a["레이디의 거주 지역"] == b["레이디의 거주 지역"]: s+=1; hit.append("거리")
    else: s+=1; t+=1; hit.append("거리무관")

    for f in ["흡연", "음주", "타투", "벽장", "퀴어 지인 多"]:
        if f+"(레이디)" in a and f+"(상대방)" in b:
            if a[f+"(레이디)"] == b[f+"(상대방)"] or b[f+"(상대방)"]=="상관없음": s+=1
            t+=1
            if b[f+"(레이디)"] == a[f+"(상대방)"] or a[f+"(상대방)"]=="상관없음": s+=1
            t+=1

    for f in ["연락 텀", "머리 길이", "데이트 선호 주기"]:
        if multi_match(a[f+"(레이디)"], b[f+"(상대방)"]): s+=1
        t+=1
        if multi_match(b[f+"(레이디)"], a[f+"(상대방)"]): s+=1
        t+=1

    if multi_match(a["성격(레이디)"], b["성격(상대방)"]): s+=1
    if multi_match(b["성격(레이디)"], a["성격(상대방)"]): s+=1
    t+=2

    if multi_match(a["양금 레벨"], b["희망 양금 레벨"]): s+=1
    t+=1
    return s, t

def matches(df):
    res, seen = [], set()
    for i, j in permutations(df.index, 2):
        A, B = df.loc[i], df.loc[j]
        pair = tuple(sorted([A["닉네임"], B["닉네임"]]))
        if pair in seen: continue
        seen.add(pair)

        sc, tot = score(A, B)
        res.append({"A": pair[0], "B": pair[1], "점수": sc, "총": tot, "비율(%)": round(sc/tot*100,1)})
    return pd.DataFrame(res).sort_values("비율(%)", ascending=False)

# ---------- 실행 ----------
if raw_txt:
    try:
        raw = pd.read_csv(StringIO(raw_txt), sep="\t")
        df  = clean_df(raw)
        st.success("✅ 정제 완료")

        req = ["닉네임","레이디 키","상대방 레이디 키","레이디 나이","선호하는 상대방 레이디 나이"]
        miss = [c for c in req if c not in df.columns]
        if miss:
            st.error(f"❌ 필수 컬럼 누락: {miss}")
            st.write(df.columns.tolist())
            st.stop()

        result = matches(df)
        st.subheader("💘 매칭 결과")
        st.dataframe(result if not result.empty else "조건에 맞는 매칭이 없습니다.")

    except Exception as e:
        st.error(f"❌ 분석 실패: {e}")
