interface Env {
  RESEND_API_KEY?: string
  DEMO_REQUEST_TO_EMAIL?: string
  DEMO_REQUEST_FROM_EMAIL?: string
  TURNSTILE_SECRET_KEY?: string
}

interface PagesContext {
  env: Env
  request: Request
}

type DemoRequest = {
  name?: unknown
  email?: unknown
  preferred_time?: unknown
  audience?: unknown
  message?: unknown
  company?: unknown
  turnstile_token?: unknown
}

const json = (body: Record<string, unknown>, status = 200) => new Response(JSON.stringify(body), {
  status,
  headers: { 'Content-Type': 'application/json; charset=utf-8' },
})

const text = (value: unknown, maximum: number) => typeof value === 'string' ? value.trim().slice(0, maximum) : ''
const escapeHtml = (value: string) => value.replace(/[&<>'"]/g, (character) => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;',
}[character] ?? character))

export async function onRequestPost(context: PagesContext): Promise<Response> {
  let payload: DemoRequest
  try {
    payload = await context.request.json() as DemoRequest
  } catch {
    return json({ message: 'Invalid request.' }, 400)
  }

  if (text(payload.company, 120)) return json({ message: 'Request received.' }, 202)

  const name = text(payload.name, 120)
  const email = text(payload.email, 254).toLowerCase()
  const preferredTime = text(payload.preferred_time, 80)
  const audience = text(payload.audience, 80)
  const message = text(payload.message, 1000)
  const turnstileToken = text(payload.turnstile_token, 2048)
  const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

  if (name.length < 2 || !emailPattern.test(email) || !preferredTime || !audience) {
    return json({ message: 'Please complete the required fields.' }, 400)
  }

  if (!context.env.RESEND_API_KEY || !context.env.DEMO_REQUEST_TO_EMAIL || !context.env.TURNSTILE_SECRET_KEY) {
    return json({ message: 'Demo requests are temporarily unavailable. Please try again later.' }, 503)
  }

  const turnstileBody = new FormData()
  turnstileBody.set('secret', context.env.TURNSTILE_SECRET_KEY)
  turnstileBody.set('response', turnstileToken)
  turnstileBody.set('remoteip', context.request.headers.get('CF-Connecting-IP') ?? '')
  const verification = await fetch('https://challenges.cloudflare.com/turnstile/v0/siteverify', {
    method: 'POST',
    body: turnstileBody,
  })
  const verificationResult = await verification.json() as { success?: boolean; action?: string }
  if (!verificationResult.success || verificationResult.action !== 'demo_request') {
    return json({ message: 'Verification failed. Please refresh and try again.' }, 400)
  }

  const response = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${context.env.RESEND_API_KEY}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      from: context.env.DEMO_REQUEST_FROM_EMAIL ?? 'StudyMingle <demo@thoughtmingle.com>',
      to: [context.env.DEMO_REQUEST_TO_EMAIL],
      reply_to: email,
      subject: `StudyMingle demo request from ${name}`,
      html: `<h2>New StudyMingle demo request</h2>
        <p><strong>Name:</strong> ${escapeHtml(name)}</p>
        <p><strong>Email:</strong> ${escapeHtml(email)}</p>
        <p><strong>Preferred time:</strong> ${escapeHtml(preferredTime)}</p>
        <p><strong>Audience:</strong> ${escapeHtml(audience)}</p>
        <p><strong>Message:</strong><br>${escapeHtml(message || 'Not provided').replace(/\n/g, '<br>')}</p>`,
    }),
  })

  if (!response.ok) {
    console.error('Resend rejected a StudyMingle demo request.', response.status, await response.text())
    return json({ message: 'Your request could not be sent. Please try again.' }, 502)
  }

  return json({ message: 'Request received.' }, 202)
}
