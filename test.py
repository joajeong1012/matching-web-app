import streamlit as st
import pandas as pd
from io import StringIO
from itertools import permutations

# ---------- Streamlit UI ----------
st.set_page_config(page_title="레이디 매칭 분석기", layout="wide")
st.title("💘 레이디 이어주기 매칭 분석기")
st.markdown("#### 📋 구글 폼 응답을 복사해서 붙여넣어주세요 (TSV 형식)")
user_input = st.text_area("📥 TSV 데이터 붙여넣기", height=300)

# ---------- 전처리 함수 ----------
def clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    # 공백·개행 정리
    df.columns = (
        df.columns.str.strip()
        .str.replace("\n", " ")
        .str.replace("  +", " ", regex=True)
    )

    # ① “닉네임” 글자 들어간 열 자동 매핑
    nick_cols = [c for c in df.columns if "닉네임" in c]
    if nick_cols:
        df = df.rename(columns={nick_cols[0]: "닉네임"})

    # ② 나머지 고정 질문 매핑
    rename_dict = {
        "레이디 나이": "나이",
        "선호하는 상대방 레이디 나이": "선호 나이",
        "레이디 키를 적어주she레즈 (숫자만 적어주세여자)": "키",
        "상대방 레이디 키를 적어주she레즈 (예시 : 154~, ~170)": "선호 키",
        "레이디의 거주 지역": "지역",
        "희망하는 거리 조건": "거리 조건",
        "성격 [성격(레이디)]": "성격",
        "성격 [성격(상대방 레이디)]": "선호 성격",
        "꼭 맞아야 하는 조건들은 무엇인가레?": "꼭 조건들",
        "[머리 길이(레이디)]": "머리 길이",
        "[머리 길이(상대방 레이디)]": "선호 머리 길이",
    }
    df = df.rename(columns={k: v for k, v in rename_dict.items() if k in df.columns})

    return df

# ---------- 범위 유틸 ----------
def parse_range(txt):
    try:
        if pd.isna(txt): return None, None
        txt = str(txt).replace("이하", "~1000").replace("이상", "0~").replace(" ", "")
        if "~" in txt:
            s, e = txt.split("~")
            return float(s or 0), float(e or 1000)
        return float(txt), float(txt)
    except:
        return None, None

def is_in_range(val, rng_txt):
    try:
        val = float(val)
        mn, mx = parse_range(rng_txt)
        return mn is not None and mn <= val <= mx
    except:
        return False

def is_in_range_list(val, rngs):
    return any(is_in_range(val, r.strip()) for r in str(rngs).split(",") if r.strip())

# ---------- 조건 체크 ----------
def is_match(a, b, cond):
    if cond == "거리":
        return ("단거리" not in str(a["거리 조건"])) or (a["지역"] == b["지역"])
    if cond == "성격":
        return a["선호 성격"] in ["상관없음", b["성격"]]
    if cond == "머리 길이":
        return a.get("선호 머리 길이", "상관없음") in ["상관없음", b.get("머리 길이", "")]
    if cond == "키":
        return is_in_range(b["키"], a["선호 키"])
    # 필요시 조건 더 추가
    return True

def satisfies_all_conditions(a, b):
    musts = [c.strip() for c in str(a.get("꼭 조건들", "")).split(",") if c.strip()]
    return all(is_match(a, b, c) for c in musts)

# ---------- 매칭 점수 ----------
def match_score(a, b):
    score = total = 0
    for _a, _b in [(a, b), (b, a)]:               # 나이, 키 서로 교차 비교
        score += is_in_range_list(_a["나이"], _b["선호 나이"])
        total += 1
        score += is_in_range(_a["키"], _b["선호 키"])
        total += 1
    return score, total

# ---------- 실행 ----------
if user_input:
    try:
        raw_df = pd.read_csv(StringIO(user_input), sep="\t")
        df = clean_column_names(raw_df)
        df = df.dropna(subset=["닉네임"]).fillna("")
        df["키"] = pd.to_numeric(df["키"], errors="coerce")

        # 데이터 확인
        st.success("✅ 데이터 정제 완료!")
        with st.expander("🔍 정제된 데이터 보기"):
            st.dataframe(df)

        # 매칭 계산
        results = []
        for i, j in permutations(df.index, 2):
            A, B = df.loc[i], df.loc[j]
            if not (satisfies_all_conditions(A, B) and satisfies_all_conditions(B, A)):
                continue
            s, t = match_score(A, B)
            results.append({
                "A": A["닉네임"], "B": B["닉네임"],
                "점수": f"{s}/{t}", "퍼센트(%)": round(s / t * 100, 1) if t else 0,
            })

        res_df = pd.DataFrame(results).sort_values("퍼센트(%)", ascending=False)
        if res_df.empty:
            st.warning("😢 조건을 만족하는 매칭이 없습니다.")
        else:
            st.subheader("💘 매칭 결과")
            st.dataframe(res_df.reset_index(drop=True))

    except Exception as e:
        st.error(f"❌ 분석 실패: {e}")
