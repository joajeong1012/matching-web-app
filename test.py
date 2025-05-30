import streamlit as st
import pandas as pd
from io import StringIO
from itertools import permutations

# ===================== UI 설정 ============================
st.set_page_config(page_title="레이디 매칭 분석기", layout="wide")

st.title("💘 레이디 이어주기 매칭 분석기 2.0")
st.markdown("#### 📋 구글 폼 응답을 복사해서 붙여넣어주세요 (TSV 형식)")
st.markdown("양식: 탭으로 구분된 데이터. 전체 응답 복사 → 붙여넣기")

user_input = st.text_area("📥 응답 데이터를 붙여넣으세요", height=300)

# ===================== 유틸 함수 ============================
def clean_df(raw_df: pd.DataFrame) -> pd.DataFrame:
    """열 이름 정리 + 숫자형 변환 + 빠진 열 채우기"""
    df = raw_df.dropna(axis=1, how="all")            # 빈 열 제거
    df = df.loc[:, ~df.columns.duplicated()]         # 중복 열 제거
    df.columns = (
        df.columns.str.strip()
        .str.replace(r"\s+", " ", regex=True)        # 공백·개행 치환
    )

    # ── 열 이름 표준화 ───────────────────────────────────
    rename_map = {
        "데이트 선호 주기": "데이트 선호 주기(레이디)",
    }
    # 긴 문장으로 저장된 닉네임 열 자동 탐색 → "닉네임"으로 변경
    nick_cols = [c for c in df.columns if "닉네임" in c]
    if nick_cols:
        rename_map[nick_cols[0]] = "닉네임"
    df = df.rename(columns=rename_map)

    # ── 숫자형 컬럼 변환 ────────────────────────────────
    for col in ["레이디 키", "레이디 나이"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # ── 없는 열 기본값 채우기 (상관없음) ───────────────────
    default_missing = [
        "데이트 선호 주기(상대방)", "연락 텀(상대방)", "머리 길이(상대방)",
        "흡연(상대방)", "음주(상대방)", "타투(상대방)", "벽장(상대방)", "퀴어 지인 多(상대방)"
    ]
    for col in default_missing:
        if col not in df.columns:
            df[col] = "상관없음"

    # ── 불필요한 열 제거 ────────────────────────────────
    drop_cols = [
        "응답 시간", "손톱길이(농담)", "연애 텀", "",
        "더 추가하고 싶으신 이상언니(형)과 레이디 소개 간단하게 적어주세요!!"
    ]
    return df.drop(columns=[c for c in drop_cols if c in df.columns], errors="ignore")

def parse_range(text):
    try:
        if pd.isna(text): return (None, None)
        text = str(text).strip()
        if not text or text == "~": return (None, None)
        if "~" in text:
            a, b = text.replace(" ", "").split("~")
            return (float(a), float(b))
        return (float(text), float(text))
    except:  # 잘못된 숫자 → None
        return (None, None)

def is_in_range(val, range_text):
    try:
        val = float(val)
        low, high = parse_range(range_text)
        return low is not None and low <= val <= high
    except:
        return False

def is_in_range_list(val, range_texts):
    return any(is_in_range(val, r.strip()) for r in str(range_texts).split(",") if r.strip())

def list_overlap(list1, list2):
    return any(x.strip() in [y.strip() for y in list2] for x in list1 if x.strip())

def is_preference_match(pref_value, target_value):
    if pd.isna(pref_value) or pd.isna(target_value):
        return False
    prefs = [x.strip() for x in str(pref_value).split(",")]
    return "상관없음" in prefs or str(target_value).strip() in prefs

# ===================== 필수 조건 체크 =========================
def satisfies_must_conditions(a, b):
    musts = str(a.get("꼭 맞아야 조건들", "")).split(",")
    for m in map(str.strip, musts):
        if m == "거리" and a["희망하는 거리 조건"] == "단거리":
            if a["레이디의 거주 지역"] != b["레이디의 거주 지역"]:
                return False
        elif m == "성격":
            if not is_preference_match(a["성격(상대방)"], b["성격(레이디)"]):
                return False
        elif m == "머리 길이":
            if not is_preference_match(a["머리 길이(상대방)"], b["머리 길이(레이디)"]):
                return False
        elif m == "앙큼 레벨":
            if not list_overlap(str(a["희망 양금 레벨"]).split(","), str(b["양금 레벨"]).split(",")):
                return False
    return True

# ===================== 매칭 점수 계산 =========================
def match_score(a, b):
    score, total, matched = 0, 0, []

    # 나이
    if is_in_range_list(a["레이디 나이"], b["선호하는 상대방 레이디 나이"]):
        score += 2; matched.append("A 나이 → B 선호")
    total += 1
    if is_in_range_list(b["레이디 나이"], a["선호하는 상대방 레이디 나이"]):
        score += 2; matched.append("B 나이 → A 선호")
    total += 1

    # 키
    if is_in_range(a["레이디 키"], b["상대방 레이디 키"]):
        score += 1; matched.append("A 키 → B 선호")
    total += 1
    if is_in_range(b["레이디 키"], a["상대방 레이디 키"]):
        score += 1; matched.append("B 키 → A 선호")
    total += 1

    # 거리
    if a["희망하는 거리 조건"] == "단거리" or b["희망하는 거리 조건"] == "단거리":
        if a["레이디의 거주 지역"] == b["레이디의 거주 지역"]:
            score += 1; matched.append("거리 일치(단거리)")
        total += 1
    else:
        score += 1; matched.append("거리 무관")
        total += 1

    # 흡연·음주·타투·벽장·퀴어
    for field in ["흡연", "음주", "타투", "벽장", "퀴어 지인 多"]:
        a_self, a_pref = a.get(f"{field}(레이디)"), b.get(f"{field}(상대방)")
        b_self, b_pref = b.get(f"{field}(레이디)"), a.get(f"{field}(상대방)")
        if is_preference_match(a_pref, a_self):
            score += 1; matched.append(f"A {field}")
        total += 1
        if is_preference_match(b_pref, b_self):
            score += 1; matched.append(f"B {field}")
        total += 1

    # 연락 텀·머리 길이·데이트 주기
    for f in ["연락 텀", "머리 길이", "데이트 선호 주기"]:
        ra, rb = f + "(레이디)", f + "(상대방)"
        if is_preference_match(b[rb], a[ra]):
            score += 1; matched.append(f"A {f}")
        total += 1
        if is_preference_match(a[rb], b[ra]):
            score += 1; matched.append(f"B {f}")
        total += 1

    # 성격
    if is_preference_match(b["성격(상대방)"], a["성격(레이디)"]):
        score += 1; matched.append("A 성격")
    total += 1
    if is_preference_match(a["성격(상대방)"], b["성격(레이디)"]):
        score += 1; matched.append("B 성격")
    total += 1

    # 앙큼 레벨
    if list_overlap(str(a["양금 레벨"]).split(","), str(b["희망 양금 레벨"]).split(",")):
        score += 1; matched.append("앙금 레벨")
    total += 1

    return score, total, matched

# ===================== APP 실행 ============================
if user_input:
    try:
        raw_df = pd.read_csv(StringIO(user_input), sep="\t")
        df = clean_df(raw_df)

        st.success("✅ 데이터 분석 성공!")
        with st.expander("🔍 입력 데이터 보기"):
            st.dataframe(df)

        results, seen = [], set()
        for i, j in permutations(df.index, 2):
            a, b = df.loc[i], df.loc[j]
            pair = tuple(sorted([a["닉네임"], b["닉네임"]]))
            if pair in seen:
                continue
            seen.add(pair)
            if not (satisfies_must_conditions(a, b) and satisfies_must_conditions(b, a)):
                continue
            s, t, cond = match_score(a, b)
            pct = round(s / t * 100, 1)
            results.append({
                "A 닉네임": pair[0], "B 닉네임": pair[1],
                "매칭 점수": s, "총 점수": t,
                "비율(%)": pct, "요약": f"{s}/{t} ({pct}%)",
                "일치 조건들": ", ".join(cond)
            })

        res_df = pd.DataFrame(results).sort_values("매칭 점수", ascending=False)
        st.subheader("💘 매칭 결과")
        if res_df.empty:
            st.warning("😢 매칭 조건을 만족하는 결과가 없습니다.")
        else:
            st.dataframe(res_df)

    except Exception as e:
        st.error(f"❌ 분석 실패: {e}")
