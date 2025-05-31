import streamlit as st
import pandas as pd
from io import StringIO
from itertools import permutations

# ========== Streamlit UI ==========
st.set_page_config(page_title="💘 레이디 매칭 분석기", layout="wide")
st.title("💘 레이디 이어주기: 조건 기반 매칭 분석기")
st.markdown("""
#### 📋 아래에 TSV 응답 내용을 붙여넣고 '🔍 분석 시작' 버튼을 눌러주세요!
""")

user_input = st.text_area("📥 TSV 응답 데이터 붙여넣기", height=300)
run = st.button("🔍 분석 시작")

# ========== 전처리 ==========
def clean_column_names(df):
    df.columns = pd.io.parsers.ParserBase({'names': df.columns})._maybe_dedup_names(df.columns)
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
        '[머리 길이(레이디)]': '머리 길이',
        '[머리 길이(상대방 레이디)]': '선호 머리 길이',
        '꼭 맞아야 하는 조건들은 무엇인가레?': '꼭 조건들',
        '[흡연(레이디)]': '흡연',
        '[흡연(상대방 레이디)]': '선호 흡연',
        '[음주(레이디)]': '음주',
        '[음주(상대방 레이디) ]': '선호 음주',
        '[타투(레이디)]': '타투',
        '[타투(상대방 레이디)]': '선호 타투',
        '[벽장(레이디)]': '벽장',
        '[벽장(상대방 레이디)]': '선호 벽장',
        '[데이트 선호 주기]': '데이트 주기',
        '레이디의 앙큼 레벨': '앙큼',
        '상대방 레이디의 앙큼 레벨': '선호 앙큼',
    }
    return df.rename(columns={k: v for k, v in rename_dict.items() if k in df.columns})

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
        s, e = parse_range(txt)
        return s is not None and e is not None and s <= val <= e
    except:
        return False

def multi_in(val_list, target):
    return any(val.strip() in str(target) for val in str(val_list).split(',') if val.strip() and val.strip() != '상관없음')

def satisfies_all_conditions(a, b):
    musts = str(a.get("꼭 조건들", "")).split(',')
    for m in musts:
        m = m.strip()
        if not m: continue
        if m == "거리" and '단거리' in str(a['거리 조건']) and a['지역'] != b['지역']:
            return False
        elif m == "성격" and not multi_in(a['선호 성격'], b['성격']):
            return False
        elif m == "머리 길이" and not multi_in(a['선호 머리 길이'], b['머리 길이']):
            return False
        elif m == "키" and not is_in_range(b.get('키', 0), a.get('선호 키', "")):
            return False
        elif m == "앙큼 레벨" and not multi_in(a['선호 앙큼'], b['앙큼']):
            return False
    return True

# ========== 점수 계산 ==========
def match_score(a, b):
    score, total = 0, 0
    def add(c, result):
        nonlocal score, total
        total += 1
        if result: score += 1

    add("나이", is_in_range(a['나이'], b['선호 나이']) or is_in_range(b['나이'], a['선호 나이']))
    add("키", is_in_range(a['키'], b['선호 키']) or is_in_range(b['키'], a['선호 키']))
    add("거리", a['지역'] == b['지역'] or '단거리' not in str(a['거리 조건']) + str(b['거리 조건']))
    add("성격", multi_in(a['선호 성격'], b['성격']) or multi_in(b['선호 성격'], a['성격']))
    add("머리", multi_in(a['선호 머리 길이'], b['머리 길이']) or multi_in(b['선호 머리 길이'], a['머리 길이']))
    add("흡연", a['흡연'] == b['선호 흡연'] or b['흡연'] == a['선호 흡연'])
    add("음주", a['음주'] == b['선호 음주'] or b['음주'] == a['선호 음주'])
    add("타투", a['타투'] == b['선호 타투'] or b['타투'] == a['선호 타투'])
    add("벽장", a['벽장'] == b['선호 벽장'] or b['벽장'] == a['선호 벽장'])
    add("앙큼", multi_in(a['선호 앙큼'], b['앙큼']) or multi_in(b['선호 앙큼'], a['앙큼']))
    add("데이트 주기", True)  # 항상 비교 대상

    return score, total

# ========== 실행 ==========
if run and user_input:
    try:
        df = pd.read_csv(StringIO(user_input), sep="\t")
        df = clean_column_names(df)
        df = df.dropna(subset=['닉네임'])
        df = df[df['닉네임'].str.strip() != ""].reset_index(drop=True)

        st.success("✅ 데이터 정제 완료!")
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
                "점수": f"{s}/{t}", "퍼센트(%)": perc
            })

        res_df = pd.DataFrame(results).sort_values(by="퍼센트(%)", ascending=False)
        if res_df.empty:
            st.warning("😢 조건을 만족하는 매칭이 없습니다.")
        else:
            st.subheader("💘 매칭 결과 전체 보기")
            st.dataframe(res_df, use_container_width=True)

    except Exception as e:
        st.error(f"❌ 분석 실패: {e}")
