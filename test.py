import streamlit as st
import re                      # ← 정규식 모듈 추가
import pandas as pd
from io import StringIO
from itertools import permutations

# ---------- UI ----------
st.set_page_config(page_title="레이디 매칭 분석기", layout="wide")
st.markdown("<h1 style='color:#f76c6c;'>💘 레이디 이어주기 매칭 분석기 2.0</h1>", unsafe_allow_html=True)
raw_txt = st.text_area("📥 TSV 응답 전체를 붙여넣으세요", height=300)

# ---------- 고정 매핑 & 제거 열 ----------
column_mapping = {
    "오늘 레게팅에서 쓰실 닉네임은 무엇인가레? (오픈카톡 닉네임과 동(성)일 하게이 맞춰주she레즈)": "닉네임",
    "레이디 나이": "레이디 나이",
    "선호하는 상대방 레이디 나이": "선호하는 상대방 레이디 나이",
    "레이디의 거주 지역": "레이디의 거주 지역",
    "희망하는 거리 조건": "희망하는 거리 조건",
}
drop_columns = ["긴 or 짧 [손톱 길이 (농담)]", "34열", "28열", "타임스탬프"]

# ---------- 데이터 정제 ----------
def clean_df(df: pd.DataFrame) -> pd.DataFrame:
    # 1. 줄바꿈·따옴표 제거, 중복 공백 축소
    df.columns = [str(c).replace("\n", " ").replace('"', "").replace("  ", " ").strip()
                  for c in df.columns]
    # 2. [ ... ] 괄호 내용 제거
    df.columns = [re.sub(r"\[.*?]", "", c).strip() for c in df.columns]

    # 3. 자동 규칙 매핑
    auto = {}
    for c in df.columns:
        if "닉네임" in c:                        auto[c] = "닉네임"
        elif "레이디 키" in c and "상대방" not in c:         auto[c] = "레이디 키"
        elif "레이디 키" in c and "상대방" in c:           auto[c] = "상대방 레이디 키"
        elif "레이디 나이" in c and "상대방" not in c:     auto[c] = "레이디 나이"
        elif "나이" in c and "상대방" in c:                auto[c] = "선호하는 상대방 레이디 나이"
        elif "거주 지역" in c:                             auto[c] = "레이디의 거주 지역"
        elif "희망하는 거리 조건" in c:                    auto[c] = "희망하는 거리 조건"
        elif "흡연" in c and "상대방" not in c:            auto[c] = "흡연(레이디)"
        elif "흡연" in c and "상대방" in c:                auto[c] = "흡연(상대방)"
        elif "음주" in c and "상대방" not in c:            auto[c] = "음주(레이디)"
        elif "음주" in c and "상대방" in c:                auto[c] = "음주(상대방)"
        elif "타투" in c and "상대방" not in c:            auto[c] = "타투(레이디)"
        elif "타투" in c and "상대방" in c:                auto[c] = "타투(상대방)"
        elif "벽장" in c and "상대방" not in c:            auto[c] = "벽장(레이디)"
        elif "벽장" in c and "상대방" in c:                auto[c] = "벽장(상대방)"
        elif "성격" in c and "상대방" not in c:            auto[c] = "성격(레이디)"
        elif "성격" in c and "상대방" in c:                auto[c] = "성격(상대방)"
        elif "연락 텀" in c and "상대방" not in c:         auto[c] = "연락 텀(레이디)"
        elif "연락 텀" in c and "상대방" in c:             auto[c] = "연락 텀(상대방)"
        elif "머리 길이" in c and "상대방" not in c:       auto[c] = "머리 길이(레이디)"
        elif "머리 길이" in c and "상대방" in c:           auto[c] = "머리 길이(상대방)"
        elif "데이트 선호 주기" in c:                     auto[c] = "데이트 선호 주기(레이디)"
        elif "퀴어 지인" in c and "상대방" not in c and "多" in c:
                                                         auto[c] = "퀴어 지인 多(레이디)"
        elif "퀴어 지인" in c and "상대방" in c and "多" in c:
                                                         auto[c] = "퀴어 지인 多(상대방)"
        elif "퀴어 지인" in c and "상대방" not in c:
                                                         auto[c] = "퀴어 지인(레이디)"
        elif "퀴어 지인" in c and "상대방" in c:
                                                         auto[c] = "퀴어 지인(상대방)"
        elif "앙큼 레벨" in c and "상대방" not in c:      auto[c] = "양금 레벨"
        elif "앙큼 레벨" in c and "상대방" in c:          auto[c] = "희망 양금 레벨"
        elif "꼭 맞아야 하는 조건" in c:                  auto[c] = "꼭 맞아야 조건들"
    df = df.rename(columns=auto).rename(columns=column_mapping)

    # 4. 불필요 열 제거 + 중복 제거
    df = df.drop(columns=[c for c in drop_columns if c in df.columns], errors="ignore")
    df = df.loc[:, ~df.columns.duplicated()].fillna("")
    return df

# ---------- 범위 & 비교 유틸 ----------
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
        f = float(t); return f, f
    except ValueError:
        return (None, None)

def is_in_range(val, rng_text):
    if pd.isna(val) or pd.isna(rng_text) or str(rng_text).strip() == "":
        return False
    lo, hi = parse_range(rng_text)
    if lo is None: return False
    try:
        return lo <= float(val) <= hi
    except (ValueError, TypeError):
        return False

def is_in_range_list(val, txt):
    lst = str(txt).split(",") if pd.notna(txt) else []
    return any(is_in_range(val, s.strip()) for s in lst if s.strip())

def to_list(x):
    return [s.strip() for s in str(x).split(",")] if pd.notna(x) and str(x).strip() else []

def multi_match(a, b):
    A, B = to_list(a), to_list(b)
    return any(x in B for x in A)

# ---------- 점수 계산 ----------
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
    # 성격(예시)
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
        pair = tuple(sorted([A["닉네임"], B["
