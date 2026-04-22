export default function PrivacyPolicy() {
  return (
    <div
      className="fixed inset-0 overflow-y-auto font-landing-sans text-brand-cloud/90 antialiased"
      style={{
        background: `linear-gradient(165deg, var(--page-bg-a) 0%, var(--page-bg-b) 45%, #1c1917 100%)`,
      }}
    >
      <header className="border-b border-white/[0.06] bg-[rgb(24_24_27_/0.82)] backdrop-blur-lg">
        <div className="mx-auto flex max-w-3xl items-center gap-4 px-5 py-4 sm:px-8">
          <a href="/" className="flex items-center gap-3 hover:opacity-80 transition">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-white/10 bg-gradient-to-br from-brand-navy to-brand-slate">
              <span className="font-landing-display text-lg font-semibold tracking-tight text-brand-cloud">R</span>
            </div>
            <span className="font-landing-display text-xl font-semibold tracking-tight text-brand-cloud">Reco</span>
          </a>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-5 py-14 sm:px-8 sm:py-20">
        <h1 className="font-landing-display text-4xl font-semibold tracking-tight text-brand-cloud sm:text-5xl">
          Privacy Policy
        </h1>
        <p className="mt-3 text-sm text-brand-cloud/45">Last updated: April 21, 2026</p>

        <div className="mt-12 space-y-10 text-sm leading-relaxed text-brand-cloud/70">

          <section>
            <h2 className="font-landing-display text-xl font-semibold text-brand-cloud mb-3">Overview</h2>
            <p>
              Reco is a real estate AI assistant that helps agents manage client workspaces, documents, email threads,
              and deal timelines. This policy explains what data we collect, how we use it, and your rights as a user.
            </p>
            <p className="mt-3">
              Contractual obligations for lawful use of synced or imported data (including permissions from third
              parties) are set out in our{' '}
              <a href="/terms" className="text-brand-mint hover:text-brand-cloud transition underline underline-offset-2">
                Terms of Service
              </a>
              .
            </p>
          </section>

          <section>
            <h2 className="font-landing-display text-xl font-semibold text-brand-cloud mb-3">Information we collect</h2>
            <ul className="space-y-3">
              <li>
                <span className="text-brand-cloud/90 font-medium">Google account info</span> — When you sign in with
                Google we receive your name, email address, and profile picture via Google OAuth.
              </li>
              <li>
                <span className="text-brand-cloud/90 font-medium">Gmail data</span> — If you connect Gmail, Reco reads
                email threads associated with your clients. We store thread subjects, participant addresses, message
                dates, and body text in your account. We request read-only access and the ability to compose drafts.
                We do not send emails on your behalf without your explicit action.
              </li>
              <li>
                <span className="text-brand-cloud/90 font-medium">Google Drive data</span> — If you connect a Drive
                folder, Reco reads the files in that folder (PDFs, DOCX, TXT) to answer questions about your clients.
                We request read-only access. We do not modify or delete your Drive files.
              </li>
              <li>
                <span className="text-brand-cloud/90 font-medium">Client workspace data</span> — Notes, transaction
                details, property information, and uploaded documents you add to Reco are stored and associated with
                your account.
              </li>
              <li>
                <span className="text-brand-cloud/90 font-medium">Usage data</span> — We track the number of AI tokens
                used per account for billing and quota enforcement. We do not sell usage data.
              </li>
            </ul>
          </section>

          <section>
            <h2 className="font-landing-display text-xl font-semibold text-brand-cloud mb-3">How we use your data</h2>
            <ul className="space-y-3">
              <li>To provide the Reco service — powering AI chat responses with context from your client files, emails, and documents.</li>
              <li>To authenticate your session and associate your data with your account.</li>
              <li>To enforce subscription limits and process billing.</li>
              <li>To improve reliability and debug issues (server logs, error traces).</li>
            </ul>
            <p className="mt-4">
              We do not use your Gmail or Drive content to train AI models, and we do not share it with third parties
              except as described below.
            </p>
          </section>

          <section>
            <h2 className="font-landing-display text-xl font-semibold text-brand-cloud mb-3">Third-party AI providers</h2>
            <p>
              When you send a chat message, the relevant context (your message, client notes, document excerpts, and
              email snippets) is sent to one of the following AI providers to generate a response:
            </p>
            <ul className="mt-3 space-y-2">
              <li><span className="text-brand-cloud/90 font-medium">Anthropic</span> — Claude models (<a href="https://www.anthropic.com/privacy" target="_blank" rel="noopener noreferrer" className="text-brand-mint hover:text-brand-cloud transition underline underline-offset-2">privacy policy</a>)</li>
              <li><span className="text-brand-cloud/90 font-medium">OpenAI</span> — GPT models (<a href="https://openai.com/policies/privacy-policy" target="_blank" rel="noopener noreferrer" className="text-brand-mint hover:text-brand-cloud transition underline underline-offset-2">privacy policy</a>)</li>
              <li><span className="text-brand-cloud/90 font-medium">Google DeepMind</span> — Gemini models (<a href="https://policies.google.com/privacy" target="_blank" rel="noopener noreferrer" className="text-brand-mint hover:text-brand-cloud transition underline underline-offset-2">privacy policy</a>)</li>
            </ul>
            <p className="mt-4">
              Only the context necessary to answer your question is sent — we do not send your entire email history or
              all documents in a single request. Each provider processes your data under their own terms and privacy
              policies, which we encourage you to review.
            </p>
          </section>

          <section>
            <h2 className="font-landing-display text-xl font-semibold text-brand-cloud mb-3">Data storage and security</h2>
            <p>
              Your data is stored in a hosted PostgreSQL database. Google OAuth credentials are stored encrypted.
              Documents and files may be stored in cloud object storage. We use HTTPS for all data in transit.
            </p>
            <p className="mt-3">
              We do not share, sell, or rent your personal data or client data to any third parties outside of those
              described in this policy.
            </p>
          </section>

          <section>
            <h2 className="font-landing-display text-xl font-semibold text-brand-cloud mb-3">Google API scopes</h2>
            <p>Reco requests the following Google OAuth scopes:</p>
            <ul className="mt-3 space-y-2 font-mono text-xs text-brand-cloud/60">
              <li className="rounded-lg bg-white/[0.04] px-3 py-2">gmail.readonly — read email threads associated with your clients</li>
              <li className="rounded-lg bg-white/[0.04] px-3 py-2">gmail.compose — create draft replies from within Reco</li>
              <li className="rounded-lg bg-white/[0.04] px-3 py-2">drive.readonly — read files in a folder you designate for a client</li>
              <li className="rounded-lg bg-white/[0.04] px-3 py-2">userinfo.email — identify your account</li>
              <li className="rounded-lg bg-white/[0.04] px-3 py-2">openid — authenticate your session</li>
            </ul>
            <p className="mt-4">
              Reco's use of data obtained from Google APIs adheres to the{' '}
              <a
                href="https://developers.google.com/terms/api-services-user-data-policy"
                target="_blank"
                rel="noopener noreferrer"
                className="text-brand-mint hover:text-brand-cloud transition underline underline-offset-2"
              >
                Google API Services User Data Policy
              </a>
              , including the Limited Use requirements.
            </p>
          </section>

          <section>
            <h2 className="font-landing-display text-xl font-semibold text-brand-cloud mb-3">Data retention and deletion</h2>
            <p>
              Your data is retained as long as your account is active. You may request deletion of your account and all
              associated data at any time by contacting us. Upon deletion, your client workspaces, chat history,
              documents, and Google OAuth credentials are permanently removed.
            </p>
          </section>

          <section>
            <h2 className="font-landing-display text-xl font-semibold text-brand-cloud mb-3">Children's privacy</h2>
            <p>
              Reco is intended for professional use by real estate agents and is not directed at children under 13. We
              do not knowingly collect personal information from children.
            </p>
          </section>

          <section>
            <h2 className="font-landing-display text-xl font-semibold text-brand-cloud mb-3">Changes to this policy</h2>
            <p>
              We may update this policy from time to time. When we do, we will update the "Last updated" date at the
              top of this page. Continued use of Reco after changes constitutes acceptance of the updated policy.
            </p>
          </section>

          <section>
            <h2 className="font-landing-display text-xl font-semibold text-brand-cloud mb-3">Contact</h2>
            <p>
              For privacy questions or data deletion requests, contact us at{' '}
              <a
                href="mailto:raymorremi@gmail.com"
                className="text-brand-mint hover:text-brand-cloud transition underline underline-offset-2"
              >
                raymorremi@gmail.com
              </a>
              .
            </p>
          </section>

        </div>
      </main>

      <footer className="border-t border-white/[0.06] px-5 py-8 sm:px-8">
        <div className="mx-auto max-w-3xl text-center text-xs text-brand-cloud/40">
          <p className="font-landing-display text-sm text-brand-cloud/50">Reco</p>
          <p className="mt-2">
            <a href="/" className="hover:text-brand-cloud/70 transition">← Back to home</a>
          </p>
        </div>
      </footer>
    </div>
  )
}
