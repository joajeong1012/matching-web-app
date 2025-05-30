import streamlit as st
import pandas as pd
from io import StringIO
from itertools import permutations

# ===================== Streamlit UI =====================
st.set_page_config(page_title="레이디 매칭 분석기", layout="wide")
st.title("💘 레이디 이어주기 매칭 분석기")
st.markdown("#### 📋 구글 폼 응답을 복사해서 붙여넣어주세요 (TSV 형식)")
user_input = st.text_area("📥 TSV 데이터 붙여넣기", height=300)

# ===================== 전처리 함수 =====================
def clean_column_names(df):
    df.columns = df.columns.str.strip().str.replace("\n", "").str.replace("  +", " ", regex=True)
    rename_dict = {
        '오늘 레개팅에서 쓰실 닉네임은 무엇인가레?  (오픈카톡 닉네임과 동(성)일 하게이 맞춰주she레즈)': '닉네임',
        '레이디 나이': '나이',
        '선호하는 상대방 레이디 나이': '선호 나이',
        '레이디 키를 적어주she레즈 (숫자만 적어주세여자)': '키',
        '상대방 레이디 키를  적어주she레즈  (예시 : 154~, ~170)': '선호 키',
        '레이디의 거주 지역': '지역',
        '희망하는 거리 조건': '거리 조건',
        '성격 [성격(레이디)]': '성격',
        '성격 [성격(상대방 레이디)]': '선호 성격',
        '꼭 맞아야 하는 조건들은 무엇인가레?': '꼭 조건들',
        '[머리 길이(레이디)]': '머리 길이',
        '[머리 길이(상대방 레이디)]': '선호 머리 길이'
    }
    df = df.rename(columns={k: v for k, v in rename_dict.items() if k in df.columns})
    return df

def parse_range(txt):
    try:
        if pd.isna(txt): return None, None
        txt = str(txt).replace('이하', '~1000').replace('이상', '0~').replace(' ', '')
        if '~' in txt:
            s, e = txt.split('~')
            return float(s), float(e)
        return float(txt), float(txt)
    except:
        return None, None

def is_in_range(val, txt):
    try:
        val = float(val)
        min_val, max_val = parse_range(txt)
        if min_val is None or max_val is None: return False
        return min_val <= val <= max_val
    except:
        return False

def is_in_range_list(val, txts):
    return any(is_in_range(val, part.strip()) for part in str(txts).split(',') if part.strip())

def is_match(a, b, cond):
    if cond == "거리":
        if '단거리' in str(a['거리 조건']) and a['지역'] != b['지역']:
            return False
    elif cond == "성격":
        return a['선호 성격'] in ["상관없음", b['성격']]
    elif cond == "머리 길이":
        return a.get('선호 머리 길이', "상관없음") in ["상관없음", b.get('머리 길이', "")]
    elif cond == "키":
        return is_in_range(b.get('키', 0), a.get('선호 키', ""))
    elif cond == "데이트 주기":
        return True  # 조건 없으면 통과 처리
    return True

def satisfies_all_conditions(a, b):
    musts = str(a.get("꼭 조건들", "")).split(',')
    for m in musts:
        if m.strip() and not is_match(a, b, m.strip()):
            return False
    return True

# ===================== 매칭 점수 계산 =====================
def match_score(a, b):
    score, total = 0, 0
    if is_in_range_list(a['나이'], b['선호 나이']): score += 1
    total += 1
    if is_in_range_list(b['나이'], a['선호 나이']): score += 1
    total += 1
    if is_in_range(a['키'], b['선호 키']): score += 1
    total += 1
    if is_in_range(b['키'], a['선호 키']): score += 1
    total += 1
    return score, total

# ===================== 실행 =====================
if user_input:
    try:
        raw_df = pd.read_csv(StringIO(user_input), sep="\t")
        df = clean_column_names(raw_df)
        df = df.dropna(subset=['닉네임'])

        st.success("✅ 데이터 정제 완료!")
        with st.expander("🔍 정제된 데이터 보기"):
            st.dataframe(df)

        results = []
        for a, b in permutations(df.index, 2):
            p1, p2 = df.loc[a], df.loc[b]
            if not satisfies_all_conditions(p1, p2): continue
            if not satisfies_all_conditions(p2, p1): continue
            s, t = match_score(p1, p2)
            perc = round((s / t) * 100, 1)
            results.append({
                "A": p1['닉네임'], "B": p2['닉네임'],
                "점수": s, "총점": t, "퍼센트(%)": perc,
            })

        res_df = pd.DataFrame(results).sort_values(by="퍼센트(%)", ascending=False)
        if res_df.empty:
            st.warning("😢 조건을 만족하는 매칭이 없습니다.")
        else:
            st.subheader("💘 매칭 결과")
            st.dataframe(res_df)

    except Exception as e:
        st.error(f"❌ 분석 실패: {e}")

