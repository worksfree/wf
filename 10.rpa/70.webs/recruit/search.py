"""
삼성생명 법인영업(GFC) 자동 인재검색 & 제안 시스템
24주 MECE 사이클 + 잡코리아 필터 + 이메일 리포트 + 헤드리스
"""

import pandas as pd
import schedule
import time
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import os
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import requests
import json
from openpyxl import Workbook
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio

load_dotenv()

class SamsungLifeRecruiter:
    def __init__(self):
        self.driver = None
        self.all_candidates = pd.DataFrame()
        self.proposal_history = pd.DataFrame()
        self.week_count = 0
        self.cycle_count = 0
        
        # 24주 MECE 검색 키워드 (6개 축 x 4개 변형)
        self.search_keywords = [
            # 1) 금융 접점 (1~4주)
            '"기업금융 서울 3년이상"', '"기업금융 경기 재직중"', 
            '"여신심사 서울 5년차"', '"은행 RM 경기 근속"',
            
            # 2) 세무·회계 접점 (5~8주)
            '"법인세무 서울 성실"', '"세무대리 경기 고객중심"', 
            '"회계팀 서울 신뢰"', '"기장대리 경기 장기관계"',
            
            # 3) 구매·조달 접점 (9~12주)
            '"구매관리 서울 제조"', '"조달 경기 유통"', 
            '"협력업체관리 서울 파트너십"', '"공급망관리 경기 책임감"',
            
            # 4) 경영지원·총무 접점 (13~16주)
            '"경영지원 서울 중소기업"', '"총무팀 경기 재직중"', 
            '"인사팀 서울 팀워크"', '"노무관리 경기 안정적"',
            
            # 5) 사업관리·법무 접점 (17~20주)
            '"사업관리 서울 B2B"', '"PM 경기 관계관리"', 
            '"컴플라이언스 서울 경력"', '"법무팀 경기 체계적"',
            
            # 6) 산업현장·리스크 접점 (21~24주)
            '"품질관리 서울 제조"', '"안전관리 경기 근속"', 
            '"리스크관리 서울 신뢰"', '"계약관리 경기 협력"'
        ]
        
        # 정착률 높은 자기소개서 키워드
        self.self_keywords = [
            '성실', '꾸준함', '인내', '성과', '신뢰', '고객중심', 
            '장기관계', '팀워크', '책임감', '고객만족', '파트너십', 
            '협력', '안정적', '지속적', '루틴', '체계적', '관계관리', 
            '끈기', '노력', '헌신'
        ]

    def init_driver(self):
        """헤드리스 크롬 드라이버 초기화"""
        options = Options()
        options.add_argument('--headless')  # 헤드리스 모드
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        
        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )

    def login_jobkorea(self):
        """잡코리아 로그인"""
        self.driver.get("https://www.jobkorea.co.kr/User/LogOn/LogOn")
        wait = WebDriverWait(self.driver, 10)
        
        # ID/PW 입력
        wait.until(EC.presence_of_element_located((By.NAME, "uId")))
        self.driver.find_element(By.NAME, "uId").send_keys(os.getenv('JOBKOREA_ID'))
        self.driver.find_element(By.NAME, "pwd").send_keys(os.getenv('JOBKOREA_PW'))
        self.driver.find_element(By.XPATH, "//input[@value='로그인']").click()
        time.sleep(5)

    def apply_filters(self, week_config):
        """잡코리아 필터 적용"""
        # 지역 필터
        region_filter = week_config['region']
        # 경력 필터
        career_filter = week_config['career']
        # 최근활동 필터
        recent_filter = week_config['recent_activity']
        
        # 실제 필터 클릭 로직 (셀렉터는 실제 사이트에 맞게 조정 필요)
        time.sleep(2)

    def search_candidates(self, keyword, week_config):
        """주차별 인재 검색 + 점수화"""
        self.driver.get("https://www.jobkorea.co.kr/Recruit/Co_Read/C/personsearch")
        wait = WebDriverWait(self.driver, 10)
        
        # 검색창 입력
        search_box = wait.until(EC.presence_of_element_located((By.NAME, "stext")))
        search_box.clear()
        search_box.send_keys(keyword)
        self.driver.find_element(By.XPATH, "//button[@type='submit']").click()
        
        # 필터 적용
        self.apply_filters(week_config)
        
        candidates = []
        pages = min(3, 5)  # 최대 3페이지
        
        for page in range(pages):
            time.sleep(2)
            items = self.driver.find_elements(By.CSS_SELECTOR, ".person-list-item, .list-item")
            
            for item in items:
                try:
                    name = item.find_element(By.CSS_SELECTOR, ".name, h3").text
                    career = item.find_element(By.CSS_SELECTOR, ".career, .exp").text
                    self_intro = item.find_element(By.CSS_SELECTOR, ".self-intro, .summary").text
                    
                    # 종합점수 계산 (전체 반환 + 우선순위화)
                    score = self.score_candidate(name, career, self_intro)
                    
                    candidate = {
                        '주차': week_config['week'],
                        '키워드': keyword,
                        '이름': name,
                        '경력': career,
                        '자기소개서': self_intro[:200],
                        '종합점수': score['total'],
                        '대표접점': score['contact'],
                        '정착성': score['stability'],
                        '성과성': score['performance'],
                        '검색일': datetime.now().strftime('%Y-%m-%d %H:%M'),
                        '지역': week_config['region']
                    }
                    
                    # 3개월 내 제안 이력 확인
                    if not self.has_recent_proposal(candidate['이름']):
                        candidates.append(candidate)
                        
                except Exception as e:
                    continue
            
            # 다음 페이지
            try:
                next_btn = self.driver.find_element(By.CSS_SELECTOR, ".paging-next, .next")
                if 'disabled' not in next_btn.get_attribute('class'):
                    next_btn.click()
                else:
                    break
            except:
                break
        
        return sorted(candidates, key=lambda x: x['종합점수'], reverse=True)

    def score_candidate(self, name, career, self_intro):
        """후보자 종합점수 계산"""
        score = {
            'contact': 0,      # 대표 접점
            'stability': 0,    # 정착성
            'performance': 0,  # 성과성
            'total': 0
        }
        
        # 1. 대표 접점 점수
        contact_keywords = ['금융', '세무', '구매', '조달', '총무', '인사', '사업관리', '리스크']
        score['contact'] = sum(1 for k in contact_keywords if k in career)
        
        # 2. 정착성 점수 (자소서 키워드)
        intro_lower = self_intro.lower()
        score['stability'] = sum(1 for k in self.self_keywords if k in intro_lower)
        
        # 3. 성과성 점수
        perf_keywords = ['성과', '실적', '타겟', '목표', '성과관리']
        score['performance'] = sum(1 for k in perf_keywords if k in intro_lower)
        
        # 4. 안정성 보너스
        stability_bonus = 0
        if '재직' in career or '근속' in career:
            stability_bonus += 2
        if '3년' in career or '5년' in career:
            stability_bonus += 1
        
        score['total'] = score['contact'] * 3 + score['stability'] * 2 + score['performance'] + stability_bonus
        return score

    def has_recent_proposal(self, name):
        """3개월 내 제안 이력 확인"""
        if len(self.proposal_history) == 0:
            return False
        
        recent = self.proposal_history[
            (pd.to_datetime(self.proposal_history['제안일']) > 
             datetime.now() - timedelta(days=90))
        ]
        return name in recent['이름'].values

    def send_proposal(self, candidate):
        """입사 제안 발송"""
        proposal = f"""
안녕하세요, {candidate['이름']}님

삼성생명(주)으로부터 채용의뢰를 받은 용산HR 이인성 팀장입니다.

"{candidate['자기소개서'][:50]}..."에서 보이는 
{candidate['경력']} 경험과 {candidate['정착성']}점의 
성실함, 고객중심 철학이 매우 인상적이었습니다.

현재 모집중인 법인영업(GFC)은 기업 대표를 대상으로 
세무·재무·리스크 컨설팅하는 전문직입니다.

"교육의 삼성"답게 입사 후 13개월간
- 세무사·회계사·노무사 강의
- CEO아카데미, 기업보장분석 프로그램  
- 1:1 선배 멘토링 체계

를 통해 무경험자도 법인전문가로 키웁니다.

관심 있으시면 10분 정도 통화로 자세히 설명드릴까요?

이인성 팀장 | 삼성생명 용산HR | 010-XXXX-XXXX
"""
        # 잡코리아 입사제안 API 호출 (실제 구현 필요)
        print(f"✅ 제안 발송 완료: {candidate['이름']} (점수: {candidate['종합점수']})")
        
        # 제안 이력 저장
        proposal_record = {
            '이름': candidate['이름'],
            '주차': candidate['주차'],
            '점수': candidate['종합점수'],
            '제안일': datetime.now().strftime('%Y-%m-%d %H:%M')
        }
        self.proposal_history = pd.concat([
            self.proposal_history,
            pd.DataFrame([proposal_record])
        ], ignore_index=True)

    def generate_report(self):
        """주간 리포트 생성 + 차트"""
        df = self.all_candidates[self.all_candidates['주차'] == self.week_count]
        
        # Plotly 차트 생성
        fig = px.bar(
            df.nlargest(10, '종합점수')[['이름', '종합점수']],
            x='종합점수', y='이름',
            title=f"{self.week_count}주차 Top 10 후보 (총 {len(df)}명 검색)",
            orientation='h'
        )
        fig.update_layout(width=800, height=600)
        fig.write_image(f"weekly_report_w{self.week_count}.png")
        
        # 엑셀 저장
        df.to_excel(f'candidates_w{self.week_count}.xlsx', index=False)
        self.proposal_history.to_excel('proposal_history.xlsx', index=False)

    def send_email_report(self):
        """이메일 리포트 발송"""
        msg = MIMEMultipart()
        msg['From'] = os.getenv('SENDER_EMAIL')
        msg['To'] = os.getenv('REPORT_EMAIL')
        msg['Subject'] = f"[{self.week_count}주차] 법인영업 후보 검색 리포트"
        
        body = f"""
{self.week_count}주차 자동 검색 완료

검색 키워드: {self.search_keywords[(self.week_count-1)%24]}
후보 수: {len(self.all_candidates[self.all_candidates['주차']==self.week_count])}명
제안 발송: {len(self.proposal_history[self.proposal_history['주차']==self.week_count])}명
평균 점수: {self.all_candidates[self.all_candidates['주차']==self.week_count]['종합점수'].mean():.1f}

차트와 엑셀 첨부했습니다.
"""
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # 차트 첨부
        with open(f"weekly_report_w{self.week_count}.png", "rb") as f:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename=weekly_report_w{self.week_count}.png'
            )
            msg.attach(part)
        
        # 이메일 발송
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(os.getenv('SENDER_EMAIL'), os.getenv('EMAIL_PASSWORD'))
        server.send_message(msg)
        server.quit()
        
        print("📧 이메일 리포트 발송 완료")

    def run_weekly(self):
        """주간 자동 실행 (금요일 11시)"""
        self.week_count += 1
        if self.week_count > 24:
            self.cycle_count += 1
            self.week_count = 1
            print(f"🎉 1사이클 완료! {self.cycle_count}사이클 시작")
        
        # 주차별 설정 (필터 조합)
        week_configs = {
            1: {'week': 1, 'region': '서울', 'career': '3년이상', 'recent_activity': '30일'},
            2: {'week': 2, 'region': '경기', 'career': '재직중', 'recent_activity': '90일'},
            # ... 24주까지 동일 패턴
        }
        week_config = week_configs.get(self.week_count, week_configs[1])
        
        keyword = self.search_keywords[(self.week_count-1) % 24]
        
        print(f"🚀 [{datetime.now()}] {self.week_count}주차 시작: {keyword}")
        
        # 검색 실행
        candidates = self.search_candidates(keyword, week_config)
        self.all_candidates = pd.concat([
            self.all_candidates, pd.DataFrame(candidates)
        ], ignore_index=True)
        
        # 제안 발송 (점수 상위 70% 대상)
        high_score_candidates = [c for c in candidates if c['종합점수'] >= 5]
        for candidate in high_score_candidates:
            self.send_proposal(candidate)
        
        # 리포트 생성 및 발송
        self.generate_report()
        self.send_email_report()
        
        print(f"✅ {self.week_count}주차 완료: {len(candidates)}명 검색, {len(high_score_candidates)}명 제안")

    def start_scheduler(self):
        """스케줄러 시작 (매주 금요일 11시)"""
        schedule.every().friday.at("11:00").do(self.run_weekly)
        
        print("⏰ 스케줄러 시작 - 매주 금요일 11시 실행")
        print("종료하려면 Ctrl+C")
        
        while True:
            schedule.run_pending()
            time.sleep(60)

if __name__ == "__main__":
    recruiter = SamsungLifeRecruiter()
    recruiter.init_driver()
    recruiter.login_jobkorea()
    recruiter.start_scheduler()