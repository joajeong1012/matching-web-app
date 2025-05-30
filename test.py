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
    df = raw_df.dropna(how="all")  # 전체가 비어있는 줄 제거
    df = df.dropna(axis=1, how="all")  # 전체가 비어있는 열 제거
    df = df.replace({pd.NA: None}).fillna("")  # NA 및 None → 빈 문자열

    rename_map = {
        df.columns[1]: "닉네임",
        "레이디 키를 적어주she레즈 (숫자만 적어주세여자)": "레이디 키",
        "상대방 레이디 키를  적어주she레즈  (예시 : 154~, ~170)": "상대방 레이디 키",
        "레이디의 앙큼 레벨": "양금 레벨",
        "상대방 레이디의 앙큼 레벨": "희망 양금 레벨",
        "꼭 맞아야 하는 조건들은 무엇인가레?": "꼭 맞아야 조건들",
        "성격 [성격(레이디)]": "성격(레이디)",
        "성격 [성격(상대방 레이디)]": "성격(상대방)",
        " [머리 길이(레이디)]": "머리 길이(레이디)",
        " [머리 길이(상대방 레이디)]": "머리 길이(상대방)",
    }

    df = df.rename(columns=rename_map)
    return df

def is_preference_match(preference_value, target_value):
    if not preference_value or not target_value:
        return False
    pref_list = [x.strip() for x in str(preference_value).split(",")]
    return "상관없음" in pref_list or str(target_value).strip() in pref_list

def list_overlap(list1, list2):
    return any(a.strip() in [b.strip() for b in list2] for a in list1 if a.strip())

def satisfies_must_conditions(person_a, person_b):
    musts = str(person_a.get("꼭 맞아야 조건들", "")).split(",")
    for cond in musts:
        cond = cond.strip()
        if cond == "거리":
            if person_a.get("희망하는 거리 조건\n", "") == "단거리":
                if person_a.get("레이디의 거주 지역") != person_b.get("레이디의 거주 지역"):
                    return False
        elif cond == "성격":
            if not is_preference_match(person_a.get("성격(상대방)", ""), person_b.get("성격(레이디)", "")):
                return False
        elif cond == "머리 길이":
            if not is_preference_match(person_a.get("머리 길이(상대방)", ""), person_b.get("머리 길이(레이디)", "")):
                return False
        elif cond == "앙큼 레벨":
            if not list_overlap(
                str(person_a.get("희망 양금 레벨", "")).split(","),
                str(person_b.get("양금 레벨", "")).split(",")
            ):
                return False
    return True

def match_score(a, b):
    score, total = 0, 0
    matched = []

    if is_preference_match(b.get("성격(상대방)", ""), a.get("성격(레이디)", "")):
        score += 1
        matched.append("A 성격")
    total += 1
    if is_preference_match(a.get("성격(상대방)", ""), b.get("성격(레이디)", "")):
        score += 1
        matched.append("B 성격")
    total += 1

    if list_overlap(
        str(a.get("양금 레벨", "")).split(","),
        str(b.get("희망 양금 레벨", "")).split(",")
    ):
        score += 1
        matched.append("앙금 레벨")
    total += 1

    return score, total, matched

# ===================== 실행 ============================
if user_input:
    try:
        raw_df = pd.read_csv(StringIO(user_input), sep="\t")
        df = clean_df(raw_df)

        st.success("✅ 데이터 정제 완료!")
        with st.expander("🔍 정제된 데이터 보기"):
            st.dataframe(df)

        matches = []
        seen = set()
        for a, b in permutations(df.index, 2):
            pa, pb = df.loc[a], df.loc[b]
            pair = tuple(sorted([pa.get("닉네임"), pb.get("닉네임")]))
            if pair in seen: continue
            seen.add(pair)
            if not satisfies_must_conditions(pa, pb) or not satisfies_must_conditions(pb, pa):
                continue
            s, t, conds = match_score(pa, pb)
            percent = round((s / t) * 100, 1) if t else 0
            matches.append({
                "A 닉네임": pair[0],
                "B 닉네임": pair[1],
                "매칭 점수": s,
                "총 점수": t,
                "비율(%)": percent,
                "요약": f"{s} / {t}점 ({percent}%)",
                "일치 조건들": ", ".join(conds)
            })

        result_df = pd.DataFrame(matches).sort_values(by="매칭 점수", ascending=False)
        st.subheader("💘 매칭 결과")
        if result_df.empty:
            st.warning("😢 매칭 조건을 만족하는 결과가 없습니다.")
        else:
            st.dataframe(result_df)

    except Exception as e:
        st.error(f"❌ 분석 실패: {e}")
