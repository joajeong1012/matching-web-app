import streamlit as st
import pandas as pd
from io import StringIO
from itertools import permutations

# ===================== 페이지 설정 ============================
st.set_page_config(page_title="레이디 매칭 분석기", layout="wide")
st.markdown("<h1 style='color:#f76c6c;'>💘 레이디 이어주기 매칭 분석기 2.0</h1>", unsafe_allow_html=True)
st.markdown("#### 📋 구글 폼 응답을 복사해서 붙여넣어주세요 (TSV 형식)")
st.info("전체 응답을 복사→붙여넣으면 자동 분석됩니다. 줄바꿈·복수응답·NaN 모두 OK!")

user_input = st.text_area("📥 응답 데이터를 붙여넣으세요", height=300)

# ===================== (필요시) 고정 매핑 테이블 ============================
column_mapping = {
    "오늘 레게팅에서 쓰실 닉네임은 무엇인가레? (오픈카톡 닉네임과 동(성)일 하게이 맞춰주she레즈)": "닉네임",
    "레이디 나이": "레이디 나이",
    "선호하는 상대방 레이디 나이": "선호하는 상대방 레이디 나이",
    "레이디의 거주 지역": "레이디의 거주 지역",
    "희망하는 거리 조건": "희망하는 거리 조건",
    # ↓ 아래 항목은 자동 매핑 규칙으로 대체될 수도 있지만 남겨두면 안전
    "레이디 키": "레이디 키",
    "상대방 레이디 키": "상대방 레이디 키",
    "흡연(레이디)": "흡연(레이디)",     "흡연(상대방)": "흡연(상대방)",
    "음주(레이디)": "음주(레이디)",     "음주(상대방)": "음주(상대방)",
    "타투(레이디)": "타투(레이디)",     "타투(상대방)": "타투(상대방)",
    "벽장(레이디)": "벽장(레이디)",     "벽장(상대방)": "벽장(상대방)",
    "성격(레이디)": "성격(레이디)",     "성격(상대방)": "성격(상대방)",
    "연락 텀(레이디)": "연락 텀(레이디)","연락 텀(상대방)": "연락 텀(상대방)",
    "머리 길이(레이디)": "머리 길이(레이디)","머리 길이(상대방)": "머리 길이(상대방)",
    "데이트 선호 주기(레이디)": "데이트 선호 주기(레이디)",
    "퀴어 지인(레이디)": "퀴어 지인(레이디)","퀴어 지인(상대방)": "퀴어 지인(상대방)",
    "퀴어 지인 多(레이디)": "퀴어 지인 多(레이디)","퀴어 지인 多(상대방)": "퀴어 지인 多(상대방)",
    "양금 레벨": "양금 레벨","희망 양금 레벨": "희망 양금 레벨",
    "꼭 맞아야 조건들": "꼭 맞아야 조건들",
}

drop_columns = [
    "긴 or 짧 [손톱 길이 (농담)]", "34열", "28열",
    "타임스탬프", "더 추가하고 싶으신 이상언니(형)과 레이디 소개 간단하게 적어주세요!!"
]

# ===================== 데이터 정리 ============================
def clean_df(raw_df: pd.DataFrame) -> pd.DataFrame:
    # 1) 줄바꿈·따옴표·중복 공백 제거
    raw_df.columns = [str(c).replace("\n", " ").replace('"', "").replace("  ", " ").strip()
                      for c in raw_df.columns]

    # 2) 자동 규칙 매핑 (키워드 포함 여부)
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
        # 필요한 키워드 패턴을 계속 추가해주면 됨
    raw_df = raw_df.rename(columns=auto_map)

    # 3) 고정 매핑 적용
    raw_df = raw_df.rename(columns=column_mapping)

    # 4) 불필요 열 제거·중복 컬럼 제거
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
    l1 = [str(a).strip() for a in list1 if pd.notna(a)]
    l2 = [str(b).strip() for b in list2 if pd.notna(b)]
    return any(a in l2 for a in l1)

def multi_value_match(val1, val2):
    v1_list = [str(v).strip() for v in str(val1).split(",")] if pd.notna(val1) else []
    v2_list = [str(v).strip() for v in str(val2).split(",")] if pd.notna(val2) else []
    return any(v1 in v2_list for v1 in v1_list)

# ===================== 조건 비교 ============================
def satisfies_must_conditions(a, b):
    musts = str(a.get("꼭 맞아야 조건들", "")).split(",")
    for cond in musts:
        cond = cond.strip()
        if cond == "거리" and "단거리" in a["희망하는 거리 조건"]:
            if a["레이디의 거주 지역"] != b["레이디의 거주 지역"]:
                return False
        elif cond == "성격":
            if not multi_value_match(b["성격(레이디)"], a["성격(상대방)"]):
                return False
        elif cond == "머리 길이":
            if not multi_value_match(b["머리 길이(레이디)"], a["머리 길이(상대방)"]):
                return False
        elif cond == "앙큼 레벨":
            if not list_overlap(str(a["희망 양금 레벨"]).split(","), 
                                str(b["양금 레벨"]).split(",")):
                return False
    return True

# ===================== 점수 계산 ============================
def match_score(a, b):
    s, t, hit = 0, 0, []

    # 나이
    if is_in_range_list(a["레이디 나이"], b["선호하는 상대방 레이디 나이"]):
        s += 2; hit.append("A 나이→B 선호")
    t += 1
    if is_in_range_list(b["레이디 나이"], a["선호하는 상대방 레이디 나이"]):
        s += 2; hit.append("B 나이→A 선호")
    t += 1

    # 키
    if is_in_range(a["레이디 키"], b["상대방 레이디 키"]):
        s += 1; hit.append("A 키→B 선호")
    t += 1
    if is_in_range(b["레이디 키"], a["상대방 레이디 키"]):
        s += 1; hit.append("B 키→A 선호")
    t += 1

    # 거리
    if "단거리" in a["희망하는 거리 조건"] or "단거리" in b["희망하는 거리 조건"]:
        if a["레이디의 거주 지역"] == b["레이디의 거주 지역"]:
            s += 1; hit.append("단거리 일치")
        t += 1
    else:
        s += 1; hit.append("거리 무관"); t += 1

    # 흡연/음주/타투/벽장/퀴어多
    for fld in ["흡연", "음주", "타투", "벽장", "퀴어 지인 多"]:
        if a[fld+"(상대방)"] in ["상관없음", a[fld+"(레이디)"]]: s += 1; hit.append(f"A {fld}"); 
        t += 1
        if b[fld+"(상대방)"] in ["상관없음", b[fld+"(레이디)"]]: s += 1; hit.append(f"B {fld}");
        t += 1

    # 연락텀/머리길이/데이트주기
    for fld in ["연락 텀", "머리 길이", "데이트 선호 주기"]:
        if multi_value_match(a[fld+"(레이디)"], b[fld+"(상대방)"]): s += 1; hit.append(f"A {fld}"); 
        t += 1
        if multi_value_match(b[fld+"(레이디)"], a[fld+"(상대방)"]): s += 1; hit.append(f"B {fld}");
        t += 1

    # 성격
    if multi_value_match(a["성격(레이디)"], b["성격(상대방)"]): s += 1; hit.append("A 성격"); 
    t += 1
    if multi_value_match(b["성격(레이디)"], a["성격(상대방)"]): s += 1; hit.append("B 성격"); 
    t += 1

    # 앙큼 레벨
    if list_overlap(str(a["양금 레벨"]).split(","), str(b["희망 양금 레벨"]).split(",")):
        s += 1; hit.append("앙큼 레벨")
    t += 1

    return s, t, hit

# ===================== 매칭 테이블 ============================
def get_matches(df):
    if "닉네임" not in df.columns:
        st.error("❌ '닉네임' 컬럼이 없습니다. 컬럼명 확인 요망!")
        st.stop()

    out, seen = [], set()
    for i, j in permutations(df.index, 2):
        A, B = df.loc[i], df.loc[j]
        pair = tuple(sorted([A["닉네임"], B["닉네임"]]))
        if pair in seen: continue
        seen.add(pair)

        if not (satisfies_must_conditions(A, B) and satisfies_must_conditions(B, A)):
            continue

        sc, tot, conds = match_score(A, B)
        pct = round(sc/tot*100, 1)
        out.append({"A 닉네임": pair[0], "B 닉네임": pair[1],
                    "매칭 점수": sc, "총 점수": tot,
                    "비율(%)": pct, "일치 조건": ", ".join(conds)})
    return pd.DataFrame(out).sort_values("비율(%)", ascending=False)

# ===================== 실행 ============================
if user_input:
    try:
        raw = pd.read_csv(StringIO(user_input), sep="\t")
        df  = clean_df(raw)

        st.success("✅ 데이터 정제 완료!")
        with st.expander("📊 정제된 데이터 확인"):
            st.dataframe(df)

        # 필수 컬럼 존재 체크
        required = ["닉네임", "레이디 키", "상대방 레이디 키", "레이디 나이",
                    "선호하는 상대방 레이디 나이", "희망하는 거리 조건"]
        miss = [c for c in required if c not in df.columns]
        if miss:
            st.error(f"❌ 필수 컬럼 누락: {miss}")
            st.stop()

        result = get_matches(df)
        st.subheader("💘 매칭 결과")
        if result.empty:
            st.warning("😢 조건을 만족하는 매칭이 없습니다.")
        else:
            st.dataframe(result)

    except Exception as e:
        st.error(f"❌ 분석 실패: {e}")
