import streamlit as st
import pandas as pd
from io import StringIO
from itertools import permutations

# ===================== 페이지 설정 ============================
st.set_page_config(page_title="레이디 매칭 분석기", layout="wide")
st.markdown("<h1 style='color:#f76c6c;'>💘 레이디 이어주기 매칭 분석기 2.0</h1>", unsafe_allow_html=True)
st.markdown("#### 📋 구글 폼 응답(전체)을 TSV로 복사해 붙여넣어주세요")
st.info("줄바꿈·복수응답·NaN 모두 자동 처리됩니다!")

user_input = st.text_area("📥 TSV 응답 데이터를 붙여넣으세요", height=300)

# ===================== 고정 매핑(있으면 편함) ============================
column_mapping = {
    "오늘 레게팅에서 쓰실 닉네임은 무엇인가레? (오픈카톡 닉네임과 동(성)일 하게이 맞춰주she레즈)": "닉네임",
    "레이디 나이": "레이디 나이",
    "선호하는 상대방 레이디 나이": "선호하는 상대방 레이디 나이",
    "레이디의 거주 지역": "레이디의 거주 지역",
    "희망하는 거리 조건": "희망하는 거리 조건",
    # 나머지 컬럼은 자동 규칙 매핑으로 잡아도 되지만 안전차원으로 일부 넣어둠
}

drop_columns = [
    "긴 or 짧 [손톱 길이 (농담)]", "34열", "28열",
    "타임스탬프", "더 추가하고 싶으신 이상언니(형)과 레이디 소개 간단하게 적어주세요!!"
]

# ===================== 데이터 정리 ============================
def clean_df(raw_df: pd.DataFrame) -> pd.DataFrame:
    # 1) 줄바꿈‧따옴표‧중복 공백 제거
    raw_df.columns = [str(c).replace("\n", " ").replace('"', "").replace("  ", " ").strip()
                      for c in raw_df.columns]

    # 2) 자동 규칙 매핑
    auto_map = {}
    for c in raw_df.columns:
        if "닉네임" in c:                    auto_map[c] = "닉네임"
        elif "레이디 키" in c and "상대방" not in c:
                                             auto_map[c] = "레이디 키"
        elif ("레이디 키" in c and "상대방" in c) or "상대방 레이디 키" in c:
                                             auto_map[c] = "상대방 레이디 키"
        elif "레이디 나이" in c and "상대방" not in c:
                                             auto_map[c] = "레이디 나이"
        elif "나이" in c and "상대방" in c:
                                             auto_map[c] = "선호하는 상대방 레이디 나이"
        elif "거주 지역" in c:               auto_map[c] = "레이디의 거주 지역"
        elif "희망하는 거리 조건" in c:      auto_map[c] = "희망하는 거리 조건"
        elif "(레이디)" in c and "흡연" in c: auto_map[c] = "흡연(레이디)"
        elif "(상대방" in c and "흡연" in c: auto_map[c] = "흡연(상대방)"
        elif "(레이디)" in c and "음주" in c: auto_map[c] = "음주(레이디)"
        elif "(상대방" in c and "음주" in c: auto_map[c] = "음주(상대방)"
        # 필요한 규칙을 추가로 적으면 끝

    raw_df = raw_df.rename(columns=auto_map)
    raw_df = raw_df.rename(columns=column_mapping)

    # 3) 불필요 열 제거·중복 제거
    raw_df = raw_df.drop(columns=[c for c in drop_columns if c in raw_df.columns], errors="ignore")
    raw_df = raw_df.loc[:, ~raw_df.columns.duplicated()]
    return raw_df

# ===================== 유틸 ============================
def parse_range(text):
    try:
        if pd.isna(text): return None, None
        text = str(text).strip()
        if not text or text == "~": return None, None
        if "~" in text:
            lo, hi = text.replace(" ", "").split("~")
            return float(lo), float(hi) if hi else (None, None)
        return float(text), float(text)
    except: return None, None

def is_in_range(val, range_text):
    try:
        if pd.isna(val) or pd.isna(range_text): return False
        v = float(str(val).strip())
        lo, hi = parse_range(range_text)
        return lo <= v <= hi if lo is not None else False
    except: return False

def is_in_range_list(val, range_texts):
    rngs = str(range_texts).split(",") if pd.notna(range_texts) else []
    return any(is_in_range(val, r.strip()) for r in rngs if r.strip())

def list_overlap(list1, list2):
    l1 = [str(a).strip() for a in (list1 if hasattr(list1, "__iter__") else [list1]) if pd.notna(a)]
    l2 = [str(b).strip() for b in (list2 if hasattr(list2, "__iter__") else [list2]) if pd.notna(b)]
    return any(a in l2 for a in l1)

def multi_value_match(val1, val2):
    v1_list = [s.strip() for s in str(val1).split(",")] if pd.notna(val1) else []
    v2_list = [s.strip() for s in str(val2).split(",")] if pd.notna(val2) else []
    return any(v in v2_list for v in v1_list if v)

# ===================== 조건 비교 ============================
def satisfies_must(a, b):
    musts = str(a.get("꼭 맞아야 조건들", "")).split(",")
    for m in musts:
        m = m.strip()
        if m == "거리" and "단거리" in a["희망하는 거리 조건"]:
            if a["레이디의 거주 지역"] != b["레이디의 거주 지역"]: return False
        elif m == "성격":
            if not multi_value_match(b["성격(레이디)"], a["성격(상대방)"]): return False
        elif m == "머리 길이":
            if not multi_value_match(b["머리 길이(레이디)"], a["머리 길이(상대방)"]): return False
        elif m == "앙큼 레벨":
            if not list_overlap(str(a["희망 양금 레벨"]).split(","), str(b["양금 레벨"]).split(",")):
                return False
    return True

# ===================== 점수 계산 ============================
def match_score(a, b):
    sc, tot, hit = 0, 0, []
    # 나이
    if is_in_range_list(a["레이디 나이"], b["선호하는 상대방 레이디 나이"]):
        sc += 2; hit.append("A 나이") 
    tot += 1
    if is_in_range_list(b["레이디 나이"], a["선호하는 상대방 레이디 나이"]):
        sc += 2; hit.append("B 나이")
    tot += 1
    # 키
    if is_in_range(a["레이디 키"], b["상대방 레이디 키"]):
        sc += 1; hit.append("A 키")
    tot += 1
    if is_in_range(b["레이디 키"], a["상대방 레이디 키"]):
        sc += 1; hit.append("B 키")
    tot += 1
    # 거리
    if ("단거리" in a["희망하는 거리 조건"] or "단거리" in b["희망하는 거리 조건"]):
        if a["레이디의 거주 지역"] == b["레이디의 거주 지역"]: sc += 1; hit.append("거리")
        tot += 1
    else: sc += 1; hit.append("거리 무관"); tot += 1
    # 기타
    for fld in ["흡연", "음주", "타투", "벽장", "퀴어 지인 多"]:
        if a[fld+"(상대방)"] in ["상관없음", a[fld+"(레이디)"]]: sc += 1
        tot += 1
        if b[fld+"(상대방)"] in ["상관없음", b[fld+"(레이디)"]]: sc += 1
        tot += 1
    for fld in ["연락 텀", "머리 길이", "데이트 선호 주기"]:
        if multi_value_match(a[fld+"(레이디)"], b[fld+"(상대방)"]): sc += 1
        tot += 1
        if multi_value_match(b[fld+"(레이디)"], a[fld+"(상대방)"]): sc += 1
        tot += 1
    if multi_value_match(a["성격(레이디)"], b["성격(상대방)"]): sc += 1
    tot += 1
    if multi_value_match(b["성격(레이디)"], a["성격(상대방)"]): sc += 1
    tot += 1
    if list_overlap(str(a["양금 레벨"]).split(","), str(b["희망 양금 레벨"]).split(",")):
        sc += 1
    tot += 1
    return sc, tot

# ===================== 매칭 ============================
def get_matches(df):
    if "닉네임" not in df.columns:
        st.error("❌ '닉네임' 컬럼 없음! 컬럼명 확인 필요.")
        st.stop()
    out, seen = [], set()
    for i, j in permutations(df.index, 2):
        A, B = df.loc[i], df.loc[j]
        pair = tuple(sorted([A["닉네임"], B["닉네임"]]))
        if pair in seen: continue
        seen.add(pair)
        if not (satisfies_must(A, B) and satisfies_must(B, A)): continue
        sc, tot = match_score(A, B)
        pct = round(sc/tot*100, 1)
        out.append({"A 닉네임":pair[0],"B 닉네임":pair[1],"점수":sc,"총":tot,"비율%":pct})
    return pd.DataFrame(out).sort_values("비율%")

# ===================== 실행 ============================
if user_input:
    try:
        raw = pd.read_csv(StringIO(user_input), sep="\t")
        df  = clean_df(raw)
        st.success("✅ 데이터 정제 완료!")
        with st.expander("📊 정제된 데이터 보기"):
            st.dataframe(df)

        # 필수 컬럼 검사
        must_have = ["닉네임","레이디 나이","레이디 키","상대방 레이디 키",
                     "선호하는 상대방 레이디 나이","희망하는 거리 조건"]
        miss = [c for c in must_have if c not in df.columns]
        if miss:
            st.error(f"❌ 필수 컬럼 누락: {miss}")
            st.stop()

        result = get_matches(df)
        st.subheader("💘 매칭 결과")
        if result.empty:
            st.warning("😢 조건 충족 매칭 없음")
        else:
            st.dataframe(result)

    except Exception as e:
        st.error(f"❌ 분석 실패: {e}")
