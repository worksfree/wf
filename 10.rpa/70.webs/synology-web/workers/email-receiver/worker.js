/**
 * Cloudflare Email Worker — 수신 이메일 → NAS MailPlus 브릿지
 *
 * 배포: wrangler deploy --config workers/email-receiver/wrangler.toml
 *
 * 시크릿:
 *   BRIDGE_SECRET — NAS email-bridge 인증 키 (bridge.worksfree.kr)
 *
 * 흐름:
 *   Cloudflare Email Routing → 이 Worker → bridge.worksfree.kr/email-inject
 *   → NAS localhost:25 → MailPlus
 */

export default {
  async email(message, env) {
    // raw 스트림을 직접 전달 — base64 변환 없이 CPU 부하 최소화
    const res = await fetch('https://bridge.worksfree.kr/email-inject', {
      method: 'POST',
      headers: {
        'Content-Type': 'message/rfc822',
        'x-secret':    env.BRIDGE_SECRET,
        'x-mail-from': message.from,
        'x-mail-to':   message.to,
      },
      body: message.raw,
    });

    if (!res.ok) {
      const err = await res.text();
      throw new Error(`bridge inject failed (${res.status}): ${err}`);
    }
  },
};
