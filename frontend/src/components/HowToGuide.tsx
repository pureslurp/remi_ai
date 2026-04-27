import { RecoMark } from './RecoMark'

const sections = [
  { id: 'layout', title: 'How the screen is laid out' },
  { id: 'clients', title: 'Clients (left sidebar)' },
  { id: 'chat', title: 'Chat (center)' },
  { id: 'workspace', title: 'Client workspace (right panel)' },
  { id: 'account', title: 'Profile menu (bottom-left)' },
  { id: 'tips', title: 'Easy-to-miss details' },
] as const

export default function HowToGuide() {
  return (
    <div
      className="fixed inset-0 overflow-y-auto font-landing-sans text-brand-cloud/90 antialiased"
      style={{
        background: `linear-gradient(165deg, var(--page-bg-a) 0%, var(--page-bg-b) 45%, #1c1917 100%)`,
      }}
    >
      <header className="sticky top-0 z-10 border-b border-white/[0.06] bg-[rgb(24_24_27_/0.92)] backdrop-blur-lg">
        <div className="mx-auto flex max-w-3xl flex-wrap items-center justify-between gap-3 px-5 py-4 sm:px-8">
          <div className="flex min-w-0 items-center gap-3">
            <RecoMark variant="legal" />
            <span className="font-wordmark text-xl font-semibold tracking-[0.07em] text-brand-cloud">reco-pilot</span>
            <span className="hidden text-brand-cloud/35 sm:inline">·</span>
            <span className="text-sm text-brand-cloud/55">How to use</span>
          </div>
          <a
            href="/"
            className="shrink-0 rounded-lg border border-white/15 bg-white/[0.06] px-3 py-2 text-sm text-brand-cloud/90 transition hover:border-brand-mint/40 hover:bg-white/[0.1]"
          >
            Back to app
          </a>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-5 py-10 sm:px-8 sm:py-14">
        <h1 className="font-landing-display text-3xl font-semibold tracking-tight text-brand-cloud sm:text-4xl">
          Using reco-pilot
        </h1>
        <p className="mt-3 text-sm leading-relaxed text-brand-cloud/55">
          Quick tour of the main screen, a few things the buttons don&apos;t spell out, and how buyer vs seller clients
          behave differently.
        </p>

        <nav
          aria-label="On this page"
          className="mt-8 rounded-xl border border-white/10 bg-white/[0.03] p-4 sm:p-5"
        >
          <p className="text-[11px] font-semibold uppercase tracking-wider text-brand-cloud/45">On this page</p>
          <ul className="mt-3 space-y-2 text-sm">
            {sections.map(s => (
              <li key={s.id}>
                <a href={`#${s.id}`} className="text-brand-mint/90 hover:text-brand-cloud transition underline-offset-2 hover:underline">
                  {s.title}
                </a>
              </li>
            ))}
          </ul>
        </nav>

        <div className="mt-12 space-y-12 text-sm leading-relaxed text-brand-cloud/70">
          <section id="layout">
            <h2 className="font-landing-display text-xl font-semibold text-brand-cloud mb-3">How the screen is laid out</h2>
            <p>
              Pick a client and you get three strips: your client list on the left, the conversation in the middle, and on
              the right everything about that person or couple (contact, deals, Gmail, Drive, files).
            </p>
            <p className="mt-3">
              The thin bars between columns can be dragged wider or narrower; the app remembers that on this browser. The
              little arrow and “hide” controls in the sidebar header shrink the list to icons only, or tuck it away
              completely. If you hide it, a tab on the left edge of the screen brings the list back.
            </p>
          </section>

          <section id="clients">
            <h2 className="font-landing-display text-xl font-semibold text-brand-cloud mb-3">Clients (left sidebar)</h2>
            <p>
              New Client walks you through names (you can add a spouse), whether they are buying, selling, or both, and
              any email addresses you want tied to Gmail matching later.
            </p>
            <p className="mt-3">
              Click a name to work on them. The trash can only removes what reco-pilot stored (chat, synced threads, files
              here). It does not touch their real Gmail or Google Drive.
            </p>
            <p className="mt-3">
              You will see a date and a small colored tag (buyer / seller / both). That tag is not cosmetic: it changes the
              wording on the right, how the deal section is organized, and the thin accent line along the edge of that panel.
            </p>
            <h3 className="mt-6 text-base font-semibold text-brand-cloud/90">Buyer</h3>
            <p className="mt-2">
              Green-tinted tag. The deal block is called &quot;Properties &amp; offers&quot; and each line is a house they are
              chasing or under contract on. The gray hint text in empty fields nudges you toward offer amounts, lender
              notes, inspection items, that sort of thing.
            </p>
            <h3 className="mt-5 text-base font-semibold text-brand-cloud/90">Seller</h3>
            <p className="mt-2">
              Warm gold tag. Here the block is &quot;Listing &amp; buyer offers&quot;: one listing with address and list
              price, then a line per buyer offer on that listing. The hints skew toward disclosure, staging, timelines, and
              keeping multiple offers straight on the same address.
            </p>
            <h3 className="mt-5 text-base font-semibold text-brand-cloud/90">Buyer &amp; seller</h3>
            <p className="mt-2">
              Softer neutral tag. You get the seller-style listing plus offer rows, and separate rows for homes they might
              buy. The notes area assumes you are juggling two closings, contingencies, bridge timing, that kind of mess.
            </p>
          </section>

          <section id="chat">
            <h2 className="font-landing-display text-xl font-semibold text-brand-cloud mb-3">Chat (center)</h2>
            <p>
              The assistant reads whatever you have saved for this client: notes, deal rows, uploaded files, synced
              threads, and anything you pulled from Drive. When the thread is empty, the short message in the middle is just
              a nudge about what kinds of questions work well.
            </p>
            <p className="mt-3">
              In the message box, type @ and a few letters to narrow the file list; pick a file to attach it to your next
              send. Little file tags appear under the box if you want to remove one before you hit send.
            </p>
            <p className="mt-3">
              Enter sends the message. Shift+Enter gives you a new line inside the same message. While an answer is still
              appearing, the green send icon turns into Stop so you can cut it off mid-reply if you need to.
            </p>
            <p className="mt-3">
              The two dropdowns under the box (provider and model) belong to this client only; changing them saves for the
              next time you open them. They gray out while a reply is in progress, or if your plan has hit its chat limit.
            </p>
            <p className="mt-3">
              If your account has property lookups turned on, you can start a line with{' '}
              <code className="rounded bg-white/10 px-1 py-0.5 text-[13px] text-brand-cloud/80">/search</code> or{' '}
              <code className="rounded bg-white/10 px-1 py-0.5 text-[13px] text-brand-cloud/80">/comps</code> for
              market-style pulls from a public data feed (not your MLS). The box lightly highlights when it recognizes one
              of those. Full examples sit under Property &amp; Chat commands in your profile menu when that add-on is on.
            </p>
          </section>

          <section id="workspace">
            <h2 className="font-landing-display text-xl font-semibold text-brand-cloud mb-3">Client workspace (right panel)</h2>
            <p className="mb-3">
              Each block has a title row; click the triangle to fold a section open or closed if you want more room.
            </p>
            <ul className="list-disc space-y-3 pl-5">
              <li>
                Client: name, the same buyer/seller tag, phone, and your running notes. Click out of a field and it saves by
                itself. The placeholder in the notes box changes with buyer vs seller vs both.
              </li>
              <li>
                Transactions: the deal timeline and properties tied to this person. Chat leans on whatever you put here.
              </li>
              <li>
                Documents: anything you uploaded or imported for them. These are the same files that show up when you type @
                in chat.
              </li>
              <li>
                Gmail sync (Google accounts only): mail threads pull in when one of the saved client addresses shows up on
                From, To, or Cc. You can set default subject-line rules for the whole workspace, then tighten rules per
                address when you add or expand an address. Optional start dates keep old list mail from flooding in. Sync
                fetches new mail; you can tag a thread to a deal row (if you tag by hand, a resync will not wipe that). Remove
                only removes the copy inside reco-pilot, not the real Gmail thread. Bodies feed the assistant; the Documents
                list is mostly Drive plus attachments the app turned into files.
              </li>
              <li>
                Google Drive sync (same Google-only note): paste a folder link or id, click away so it saves, then run sync.
                If you log in with email and password instead, skip this and just drop files under Documents.
              </li>
              <li>
                Clear chat history at the very bottom wipes the conversation for this client after you confirm. It leaves
                the client record, files, and Gmail sync alone.
              </li>
            </ul>
          </section>

          <section id="account">
            <h2 className="font-landing-display text-xl font-semibold text-brand-cloud mb-3">Profile menu (bottom-left)</h2>
            <p className="mb-3">Tap your picture or initial. From there:</p>
            <ul className="list-disc space-y-3 pl-5">
              <li>
                AI prompt settings pops up a full-screen style panel titled AI system prompts, with three tabs: Buying,
                Selling, and Buying &amp; selling. Think of each tab as the coaching voice reco-pilot should use for that
                kind of client. Whatever you type replaces our stock wording for your login only; the assistant still sees
                the normal deal context, files, and mail. Save writes all three tabs; Reset on a tab puts that tab back to the
                factory text.
              </li>
              <li>
                Property &amp; Chat commands only appears if your account includes the property tools. It is a cheat sheet
                for the slash commands (including{' '}
                <code className="rounded bg-white/10 px-1 py-0.5 text-[13px] text-brand-cloud/80">/search</code> and{' '}
                <code className="rounded bg-white/10 px-1 py-0.5 text-[13px] text-brand-cloud/80">/comps</code>), sample
                lines, and a blunt note about what the data is not (for example, not the MLS).
              </li>
              <li>
                Upgrade plan shows up on free or trial. You pick Pro, Max, or Ultra and pay online; higher plans mean more
                monthly assistant usage and, where we have them wired up, stronger models.
              </li>
              <li>
                Manage billing shows up once you already pay through Stripe. You get your current plan, dates or usage when
                we show them, a path to change tier, and a link out to Stripe&apos;s own page for card on file, invoices, or
                canceling. Refresh inside that panel if you changed something in another tab.
              </li>
              <li>
                Connect Google runs the standard Google permission screen so Gmail and Drive can sync. You might see it
                here or in the yellow strip at the top if you signed in with Google but never finished mail/Drive access.
                Email-and-password users use the same button to attach a Google account for sync; read the prompts so you
                pick the inbox you actually use.
              </li>
            </ul>
            <p className="mt-3">
              That yellow strip is only nagging about Google when the app thinks mail or Drive still is not hooked up.
            </p>
          </section>

          <section id="tips">
            <h2 className="font-landing-display text-xl font-semibold text-brand-cloud mb-3">Easy-to-miss details</h2>
            <ul className="list-disc space-y-2 pl-5">
              <li>
                When you are running low on included assistant usage, a quiet line appears under the model dropdowns with
                plain-language wording and a link to billing or upgrade.
              </li>
              <li>
                Privacy policy and terms of service are standalone pages (no login needed):{' '}
                <a href="/privacy" className="text-brand-mint hover:text-brand-cloud transition underline underline-offset-2">
                  privacy
                </a>
                ,{' '}
                <a href="/terms" className="text-brand-mint hover:text-brand-cloud transition underline underline-offset-2">
                  terms
                </a>
                .
              </li>
            </ul>
          </section>
        </div>
      </main>
    </div>
  )
}
