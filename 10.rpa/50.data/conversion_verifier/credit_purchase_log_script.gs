/**
 * WorksFree Credit Purchase Log - Apps Script
 * 확장형 구조: 프로모션, 보너스 크레딧 자동 계산 지원
 */

// ==================== 프로모션 코드 설정 ====================
const PROMO_CODES = {
  'LAUNCH2025': { type: 'rate', value: 0.1, description: '런칭 이벤트 10% 보너스' },
  'WELCOME': { type: 'fixed', value: 500, description: '가입 축하 500 크레딧' },
  'PREMIUM': { type: 'rate', value: 0.2, description: '프리미엄 회원 20% 보너스' },
  'FRIEND': { type: 'rate', value: 0.15, description: '친구 추천 15% 보너스' }
};

// ==================== 컬럼 인덱스 정의 (실제 시트 구조) ====================
const COL = {
  APPLIED_DATE: 1,        // A: 앱 적용 시각 (Python이 업데이트)
  TRANSACTION_ID: 2,      // B: 거래 ID (자동 생성)
  PURCHASE_DATE: 3,       // C: 구매 일시 (자동 생성)
  EMAIL: 4,               // D: 사용자 이메일 (트리거)
  APP_NAME: 5,            // E: 앱 이름
  PURCHASED_CREDIT: 6,    // F: 구매 크레딧 (기본)
  BONUS_CREDIT: 7,        // G: 보너스 크레딧 (자동 계산)
  TOTAL_CREDIT: 8,        // H: 총 크레딧 (F+G, 자동 계산)
  PRICE: 9,               // I: 결제 금액
  CHANNEL: 10,            // J: 구매 채널
  PAYMENT_METHOD: 11,     // K: 결제 수단
  PROMO_CODE: 12,         // L: 프로모션 코드
  DISCOUNT_RATE: 13,      // M: 할인율
  STATUS: 14              // N: 상태 (paid/refunded/cancelled)
};

// ==================== 메인 트리거 ====================
function onEdit(e) {
  try {
    const range = e.range;
    const sheet = range.getSheet();
    const row = range.getRow();
    const col = range.getColumn();
    
    // credit_purchase_log 시트만 처리
    if (sheet.getName() !== "credit_purchase_log") return;
    
    // 헤더 행 제외
    if (row <= 1) return;
    
    // D열(email) 입력 시 → transaction_id, purchase_date 자동 생성
    if (col === COL.EMAIL) {
      handleEmailInput(sheet, row);
    }
    
    // F열(purchased_credit) 또는 L열(promo_code) 변경 시 → 크레딧 재계산
    if (col === COL.PURCHASED_CREDIT || col === COL.PROMO_CODE) {
      calculateCredits(sheet, row);
    }
  } catch (error) {
    Logger.log("❌ onEdit 오류: " + error);
  }
}

// ==================== Email 입력 처리 ====================
function handleEmailInput(sheet, row) {
  const email = sheet.getRange(row, COL.EMAIL).getValue();
  
  // email이 비어있지 않고, transaction_id가 없을 때만 생성
  if (!email || email.toString().trim() === "") return;
  
  const currentTransactionId = sheet.getRange(row, COL.TRANSACTION_ID).getValue();
  if (currentTransactionId && currentTransactionId.toString().trim() !== "") return;
  
  // 한국 시간 기반 타임스탬프 생성
  const timestamp = getKSTTimestampWithMicroseconds();
  
  // B열: transaction_id
  sheet.getRange(row, COL.TRANSACTION_ID).setValue(timestamp);
  
  // C열: purchase_date (동일한 타임스탬프, 포맷팅)
  const formattedDate = Utilities.formatDate(new Date(), "Asia/Seoul", "yyyy-MM-dd HH:mm:ss");
  sheet.getRange(row, COL.PURCHASE_DATE).setValue(formattedDate);
  
  // N열: status 기본값
  const currentStatus = sheet.getRange(row, COL.STATUS).getValue();
  if (!currentStatus) {
    sheet.getRange(row, COL.STATUS).setValue('paid');
  }
  
  Logger.log("✅ Transaction ID 생성: " + timestamp + " (Row: " + row + ", Email: " + email + ")");
}

// ==================== 크레딧 자동 계산 ====================
function calculateCredits(sheet, row) {
  const purchasedCredit = sheet.getRange(row, COL.PURCHASED_CREDIT).getValue() || 0;
  const promoCode = sheet.getRange(row, COL.PROMO_CODE).getValue();
  
  let bonusCredit = 0;
  let discountRate = '';
  
  // 프로모션 코드가 있으면 보너스 계산
  if (promoCode && PROMO_CODES[promoCode]) {
    const promo = PROMO_CODES[promoCode];
    
    if (promo.type === 'rate') {
      bonusCredit = Math.floor(purchasedCredit * promo.value);
      discountRate = (promo.value * 100).toFixed(0) + '%';
    } else if (promo.type === 'fixed') {
      bonusCredit = promo.value;
      discountRate = promo.value + '원';
    }
    
    Logger.log("🎁 프로모션 적용: " + promoCode + " → +" + bonusCredit + " 크레딧");
  }
  
  // G열: bonus_credit
  sheet.getRange(row, COL.BONUS_CREDIT).setValue(bonusCredit);
  
  // H열: total_credit (purchased + bonus)
  const totalCredit = purchasedCredit + bonusCredit;
  sheet.getRange(row, COL.TOTAL_CREDIT).setValue(totalCredit);
  
  // M열: discount_rate
  if (discountRate) {
    sheet.getRange(row, COL.DISCOUNT_RATE).setValue(discountRate);
  }
  
  Logger.log("💰 크레딧 계산 완료: " + purchasedCredit + " + " + bonusCredit + " = " + totalCredit);
}

// ==================== 한국 시간 타임스탬프 생성 ====================
function getKSTTimestampWithMicroseconds() {
  const now = new Date();
  
  // 날짜와 시간 부분 (한국 시간대)
  const dateTime = Utilities.formatDate(now, "Asia/Seoul", "yyyy-MM-dd'T'HH:mm:ss");
  
  // 밀리초를 마이크로초 형식으로 변환 (밀리초 3자리)
  const milliseconds = now.getMilliseconds().toString().padStart(3, '0');
  
  // 최종 타임스탬프 조합
  return dateTime + ':' + milliseconds;
}

// ==================== 일괄 처리 유틸리티 ====================
/**
 * 기존 행에 대해 일괄 transaction_id 생성
 * 도구 > 스크립트 편집기 > 함수 선택해서 실행
 */
function generateMissingTransactionIds() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("credit_purchase_log");
  const lastRow = sheet.getLastRow();
  let count = 0;
  
  for (let row = 2; row <= lastRow; row++) {
    const transactionId = sheet.getRange(row, COL.TRANSACTION_ID).getValue();
    const email = sheet.getRange(row, COL.EMAIL).getValue();
    
    if (email && !transactionId) {
      const timestamp = getKSTTimestampWithMicroseconds();
      const formattedDate = Utilities.formatDate(new Date(), "Asia/Seoul", "yyyy-MM-dd HH:mm:ss");
      
      sheet.getRange(row, COL.TRANSACTION_ID).setValue(timestamp);
      sheet.getRange(row, COL.PURCHASE_DATE).setValue(formattedDate);
      
      // status가 없으면 기본값 설정
      const currentStatus = sheet.getRange(row, COL.STATUS).getValue();
      if (!currentStatus) {
        sheet.getRange(row, COL.STATUS).setValue('paid');
      }
      
      count++;
      Utilities.sleep(100); // 중복 방지
    }
  }
  
  Logger.log("✅ " + count + "개의 transaction_id 생성 완료");
  SpreadsheetApp.getUi().alert(count + "개의 transaction_id가 생성되었습니다.");
}

/**
 * 모든 행의 크레딧 재계산
 */
function recalculateAllCredits() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("credit_purchase_log");
  const lastRow = sheet.getLastRow();
  let count = 0;
  
  for (let row = 2; row <= lastRow; row++) {
    const purchasedCredit = sheet.getRange(row, COL.PURCHASED_CREDIT).getValue();
    if (purchasedCredit) {
      calculateCredits(sheet, row);
      count++;
    }
  }
  
  Logger.log("✅ " + count + "개 행의 크레딧 재계산 완료");
  SpreadsheetApp.getUi().alert(count + "개 행의 크레딧이 재계산되었습니다.");
}

/**
 * 빈 행 데이터 정리 (applied_date 기준)
 */
function cleanupEmptyRows() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("credit_purchase_log");
  const lastRow = sheet.getLastRow();
  let count = 0;
  
  // 아래에서 위로 삭제 (행 번호 변화 방지)
  for (let row = lastRow; row >= 2; row--) {
    const email = sheet.getRange(row, COL.EMAIL).getValue();
    const transactionId = sheet.getRange(row, COL.TRANSACTION_ID).getValue();
    
    // email과 transaction_id가 모두 비어있으면 삭제
    if (!email && !transactionId) {
      sheet.deleteRow(row);
      count++;
    }
  }
  
  Logger.log("✅ " + count + "개의 빈 행 삭제 완료");
  SpreadsheetApp.getUi().alert(count + "개의 빈 행이 삭제되었습니다.");
}
