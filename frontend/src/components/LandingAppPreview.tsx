import { useState, useMemo, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { Components } from 'react-markdown'
import { clientTypeSidebarPillClass } from '../lib/clientTypeStyles'
import { normalizeChatMarkdown } from '../lib/normalizeChatMarkdown'

type ClientType = 'buyer' | 'seller' | 'buyer & seller'

type PreviewClient = {
  id: string
  name: string
  type: ClientType
  dateLabel: string
  initials: string
  propertyLine: string
  offerLine: string
  gmailLine: string
  emailThreads: { subject: string; preview: string }[]
  documents: string[]
  keyDates: { label: string; date: string; urgent?: boolean }[]
}

const CLIENTS: PreviewClient[] = [
  {
    id: 'jordan',
    name: 'Jordan Rivera',
    type: 'buyer',
    dateLabel: 'Mar 18',
    initials: 'JR',
    propertyLine: '1420 Oak Lane',
    offerLine: 'Under contract $425,000 · Close May 30',
    gmailLine: 'jordan@email.com, processor@firstcapital.loans, listingagent@northside.co',
    emailThreads: [
      {
        subject: 'Re: 1420 Oak — inspection response attached',
        preview: 'Seller accepts HVAC service + GFCIs, offers $2,500 credit on roof in lieu of replacement…',
      },
      {
        subject: 'FW: Appraisal scheduled Tuesday 10am',
        preview: 'Appraiser has access via lockbox; please confirm no changes to listing condition…',
      },
      {
        subject: 'First Capital — updated LE with credit',
        preview: 'Will re-disclose once amendment is signed; rate lock still valid through May 28…',
      },
    ],
    documents: [
      'PA_executed.pdf',
      'Inspection_Report.pdf',
      'Seller_Disclosure.pdf',
      'Seller_Inspection_Response.pdf',
      'Amendment_1.docx',
      'Neighborhood_Comps_Mar.pdf',
      'FirstCapital_LE_original.pdf',
    ],
    keyDates: [
      { label: 'Inspection response due', date: 'Apr 22', urgent: true },
      { label: 'Appraisal', date: 'Apr 23' },
      { label: 'Finance contingency', date: 'May 5' },
    ],
  },
  {
    id: 'morgan',
    name: 'Morgan Lee',
    type: 'seller',
    dateLabel: 'Apr 2',
    initials: 'ML',
    propertyLine: '88 Birch Court (listing)',
    offerLine: 'Three offers received · highest & best',
    gmailLine: 'morgan@me.com, buyer.agent.A@realty.co, buyer.agent.C@realtyco.com',
    emailThreads: [
      {
        subject: '88 Birch — Offer #3 with escalation clause',
        preview: 'Escalates $1,000 over highest bona fide offer, cap $628,000, proof required…',
      },
      {
        subject: 'Re: 88 Birch — buyer inspection window',
        preview: 'Offer B buyer is requesting 12 calendar days for inspection and resale cert review…',
      },
      {
        subject: 'HOA resale package — processing ETA',
        preview: 'Management is quoting 7 calendar days from request; rush available for $150…',
      },
    ],
    documents: [
      'Listing_Agreement.pdf',
      'Seller_Net_Sheet.xlsx',
      'HOA_Resale_Bylaws.pdf',
      'Offer_A_terms.pdf',
      'Offer_B_terms.pdf',
      'Offer_C_escalation.pdf',
      'Pricing_Memo_Mar.pdf',
    ],
    keyDates: [
      { label: 'Offer decision deadline', date: 'Apr 21', urgent: true },
      { label: 'HOA resale cert delivery', date: 'Apr 28' },
      { label: 'Target accept date', date: 'Apr 22' },
    ],
  },
  {
    id: 'alex',
    name: 'Alex Park',
    type: 'buyer & seller',
    dateLabel: 'Feb 4',
    initials: 'AP',
    propertyLine: 'Sell: 45 Cedar · Buy: 210 Elm',
    offerLine: 'Contingent sale · back-to-back May 1 close',
    gmailLine: 'alex.park@gmail.com, title@anchortitle.com, loanops@firstfederal.com',
    emailThreads: [
      {
        subject: 'Title — Cedar and Elm both on our desk',
        preview: 'Confirmed same-day sequencing; need Cedar CD and Elm wiring instructions by Apr 28…',
      },
      {
        subject: 'Re: Contingent addendum v3 redlined',
        preview: 'Buyer counters shortening kick-out to 48h; see tracked changes in §3 and §7…',
      },
      {
        subject: 'First Federal — Elm loan conditions',
        preview: 'Conditional approval subject to Cedar closing proceeds and updated HOI binder…',
      },
    ],
    documents: [
      'Cedar_PA_executed.pdf',
      'Elm_PA_executed.pdf',
      'Contingent_Sale_Addendum_v3.docx',
      'Bridge_Timeline.pdf',
      'FirstFederal_CTC_checklist.pdf',
      'Cedar_Payoff_Statement.pdf',
    ],
    keyDates: [
      { label: 'Cedar buyer walkthrough', date: 'Apr 28' },
      { label: 'Both CDs finalized', date: 'Apr 29', urgent: true },
      { label: 'Back-to-back close', date: 'May 1' },
      { label: 'Elm rate lock expires', date: 'May 12' },
    ],
  },
  {
    id: 'sam',
    name: 'Sam Ortiz',
    type: 'buyer',
    dateLabel: 'Jan 30',
    initials: 'SO',
    propertyLine: '9 River Road',
    offerLine: 'CTC pending · closing Apr 24',
    gmailLine: 'sam@ortiz.family, processor@velocity.loans, escrow@anchortitle.com',
    emailThreads: [
      {
        subject: 'Velocity Loans — final conditions (4401, 4502)',
        preview: '4401: updated paystub within 30 days of funding. 4502: HOI binder effective date correction…',
      },
      {
        subject: 'Re: 9 River — CD v3 review',
        preview: 'Cash-to-close increased $1,847 vs LE; recording fee + title endorsement + actual taxes…',
      },
      {
        subject: 'Final walkthrough photos — basement',
        preview: 'Visible moisture on east foundation wall, not present at original inspection…',
      },
    ],
    documents: [
      'Closing_Disclosure_v3.pdf',
      'Loan_Estimate_original.pdf',
      'Velocity_Conditions_checklist.pdf',
      'Inspection_Report.pdf',
      'WALKTHROUGH_NOTES.txt',
      'Escrow_wiring_instructions.pdf',
      'HOI_binder.pdf',
    ],
    keyDates: [
      { label: 'Wire to escrow', date: 'Apr 23', urgent: true },
      { label: 'Final walkthrough', date: 'Apr 24' },
      { label: 'Scheduled closing', date: 'Apr 24' },
    ],
  },
  {
    id: 'taylor',
    name: 'Taylor Brooks',
    type: 'seller',
    dateLabel: 'Dec 12',
    initials: 'TB',
    propertyLine: '300 Summit Ave',
    offerLine: 'Counter #2 out · buyer side negotiating',
    gmailLine: 'taylor.b@icloud.com, buyer.agent@sawyerrealty.com, listing.broker@apex.re',
    emailThreads: [
      {
        subject: 'Counter #2 — buyer cap on credits at $10k',
        preview: 'Buyer countered your $8k cap with a $10k cap; otherwise accepts pricing at $612,500…',
      },
      {
        subject: 'Re: 300 Summit — requested contract edits',
        preview: 'Buyer side wants business-day framing on inspection response and softer financing language…',
      },
      {
        subject: 'Buyer pre-approval — Valley Bank',
        preview: 'Conventional 5.875%, 3% down assistance program, valid through May 30…',
      },
    ],
    documents: [
      'Listing_Agreement_Summit.pdf',
      'Purchase_Agreement.pdf',
      'Counter_Proposal_v2.docx',
      'Buyer_Requested_Edits.pdf',
      'Buyer_Pre-approval_ValleyBank.pdf',
      'DOM_Pricing_Memo.pdf',
    ],
    keyDates: [
      { label: 'Counter #2 expires', date: 'Apr 22', urgent: true },
      { label: 'Inspection period ends', date: 'Apr 26' },
      { label: 'Listing day 42 of 90', date: 'Apr 20' },
    ],
  },
]

type ChatTurn = { role: 'user' | 'assistant'; text: string }

/** Mirrors `ChatMessage.tsx` assistant rendering at preview scale. */
const previewAssistantMarkdownComponents: Components = {
  p: ({ children }) => <p className="mb-2 text-[11px] leading-relaxed last:mb-0">{children}</p>,
  ul: ({ children }) => (
    <ul className="mb-2 list-disc space-y-0.5 pl-4 text-[11px] marker:text-brand-mint/60">{children}</ul>
  ),
  ol: ({ children }) => (
    <ol className="mb-2 list-decimal space-y-0.5 pl-4 text-[11px] marker:text-brand-mint/60">{children}</ol>
  ),
  li: ({ children }) => (
    <li className="leading-relaxed [&>p]:mb-1 [&>p:last-child]:mb-0">{children}</li>
  ),
  strong: ({ children }) => <strong className="font-semibold text-brand-cloud">{children}</strong>,
  em: ({ children }) => <em className="italic text-brand-cloud/80">{children}</em>,
  h1: ({ children }) => (
    <h2 className="mb-1 mt-2 text-[11px] font-bold tracking-tight text-brand-cloud first:mt-0">{children}</h2>
  ),
  h2: ({ children }) => (
    <h2 className="mb-1 mt-2 text-[11px] font-bold tracking-tight text-brand-cloud first:mt-0">{children}</h2>
  ),
  h3: ({ children }) => (
    <h3 className="mb-1 mt-2 text-[11px] font-semibold text-brand-cloud first:mt-0">{children}</h3>
  ),
  hr: () => <hr className="my-2 border-white/10" />,
  blockquote: ({ children }) => (
    <blockquote className="my-2 border-l-2 border-brand-mint/60 pl-2.5 text-[11px] italic text-brand-cloud/80">
      {children}
    </blockquote>
  ),
  code: ({ children, className }) => {
    const isBlock = className?.includes('language-')
    return isBlock ? (
      <pre className="my-2 overflow-x-auto rounded-md border border-white/10 bg-black/40 p-2 text-[10px] font-mono">
        <code>{children}</code>
      </pre>
    ) : (
      <code className="rounded border border-white/10 bg-black/30 px-1 py-px text-[10px] font-mono text-brand-mint">
        {children}
      </code>
    )
  },
  table: ({ children }) => (
    <div className="-mx-0.5 my-2 overflow-x-auto rounded-md border border-white/10">
      <table className="min-w-full border-collapse text-left text-[10px]">{children}</table>
    </div>
  ),
  thead: ({ children }) => <thead className="bg-white/[0.06]">{children}</thead>,
  tbody: ({ children }) => <tbody className="divide-y divide-white/10">{children}</tbody>,
  tr: ({ children }) => <tr>{children}</tr>,
  th: ({ children }) => (
    <th className="border-r border-white/10 px-2 py-1.5 align-top text-[10px] font-semibold text-brand-cloud last:border-r-0">
      {children}
    </th>
  ),
  td: ({ children }) => (
    <td className="border-r border-white/5 px-2 py-1.5 align-top text-[10px] text-brand-cloud/90 last:border-r-0">
      {children}
    </td>
  ),
  a: ({ children, href }) => (
    <a href={href} className="text-brand-mint underline underline-offset-2 hover:text-brand-mint/90" target="_blank" rel="noreferrer">
      {children}
    </a>
  ),
}

function threadForClient(id: string): ChatTurn[] {
  switch (id) {
    case 'jordan':
      return [
        {
          role: 'user',
          text: 'Listing side sent back the inspection response. What are they actually agreeing to vs pushing back on?',
        },
        {
          role: 'assistant',
          text: `From **Re: 1420 Oak — inspection response attached** and **Seller_Inspection_Response.pdf**, the seller is taking a mixed position:

**Agreed**
- Kitchen + bath **GFCIs** replaced prior to closing
- **HVAC** serviced as outlined in the response

**Pushed back / credit instead**
- Full roof replacement → **$2,500 credit at close**
- Radon mitigation → declined (cites **Seller_Disclosure.pdf**: 3.2 pCi/L, below typical 4.0 action level)`,
        },
        {
          role: 'user',
          text: 'Is $2,500 fair for what the inspector flagged on the roof?',
        },
        {
          role: 'assistant',
          text: `**Inspection_Report.pdf** (p.14): 18-year architectural shingles with granular loss on the south face — not failing, but roughly **3–5 years** of useful life left.

**Rough cost bands (this metro)**

| Scope | Typical range |
| --- | --- |
| Partial overlay | **$8k–$12k** |
| Full tear-off | **$18k–$25k** |

**$2,500** is light against those numbers. A **$5,000** credit is a defensible counter given condition and remaining life.`,
        },
        {
          role: 'user',
          text: 'Risk that they walk if I push?',
        },
        {
          role: 'assistant',
          text: `Very low. At this stage the much more likely response is that they simply **decline the larger credit** and hope you accept the original offer rather than terminate.

If they do hold at **$2,500**, you still have choices: accept, split the difference, or walk. Sellers rarely blow up a signed deal over a few thousand dollars at inspection — they lose their buyer, reset DOM, and have to disclose everything on the next listing.`,
        },
        {
          role: 'user',
          text: 'Draft three bullets I can send to the listing agent.',
        },
        {
          role: 'assistant',
          text: `Paste-ready bullets for the listing agent:

1. Thanks for the fast turnaround on the inspection response.
2. Buyer accepts the HVAC service and GFCI replacements exactly as offered.
3. Buyer requests a **$5,000** seller credit at close on the roof in lieu of repair work — happy to sign today if that works.`,
        },
        {
          role: 'user',
          text: 'What if the appraisal comes in low?',
        },
        {
          role: 'assistant',
          text: `**PA_executed.pdf** §7 is a straight appraisal contingency **without** gap coverage. If value is under **$425,000**:

| Path | Notes |
| --- | --- |
| Seller reduces to appraised value | Cleanest if appraiser is credible |
| Split the shortfall | Meet in the middle on dollars |
| Buyer brings cash | Bridge the shortfall from outside the loan |
| Terminate + recover EM | If §7 allows and timelines work |

Because you have **not** locked yet (**First Capital — updated LE with credit**), a lender reprice is less painful than post-lock extension math.`,
        },
        {
          role: 'user',
          text: 'What am I chasing this week?',
        },
        {
          role: 'assistant',
          text: `**This week — chase list**

1. Get the credit counter signed on/before **Apr 22** (inspection response deadline in the rail).
2. Confirm Tuesday appraiser access via **FW: Appraisal scheduled Tuesday 10am**.
3. Ask First Capital to re-issue the LE once the credit is final so Jordan’s cash-to-close stays accurate before the CD.`,
        },
      ]
    case 'morgan':
      return [
        {
          role: 'user',
          text: 'Summarize the three offers side by side.',
        },
        {
          role: 'assistant',
          text: `Pulled from **Offer_A_terms.pdf**, **Offer_B_terms.pdf**, and **Offer_C_escalation.pdf**:

| Topic | **Offer A** | **Offer B** | **Offer C** |
| --- | --- | --- | --- |
| Price | **$615k** cash | **$625k** | **$608k** base, escalates to **$628k** |
| Financing | None — cash | 25% down conventional | 20% down conventional + **$15k** appraisal gap |
| Inspection | 7 days, as-is positioning | **12** calendar days requested | 10 calendar days |
| Appraisal | None | Full contingency | Partial gap protection |
| Close | 14 days | 30 days | 35 days |`,
        },
        {
          role: 'user',
          text: 'Highest and best already ran. Which one would you take?',
        },
        {
          role: 'assistant',
          text: `Ranking on **net + certainty** (what Morgan said she cares about):

1. **Offer C** — highest gross after escalation (~**$626k** against B), and the **$15k** appraisal gap helps if comps wobble.
2. **Offer B** — clean **$625k**, straightforward underwriting, no escalation proof games.
3. **Offer A** — lowest price, but fastest close and fewest moving parts — best if Morgan values **speed over price**.

If C's financing and buyer profile look solid, **C** is the natural first choice; otherwise **B** is the steadier lane.`,
        },
        {
          role: 'user',
          text: 'The 12-day inspection window on B — is that long?',
        },
        {
          role: 'assistant',
          text: `**12** calendar days is a bit longer than what you usually see (**7–10** is the common band), but it's still within a normal ask — especially on a higher-priced listing where buyers want time for specialists or a second look.

If Morgan wants to tighten it without feeling petty, **10** days is a friendly middle ground most listing agents won't fight hard on.`,
        },
        {
          role: 'user',
          text: 'How do I break the news to the two buyers we pass on?',
        },
        {
          role: 'assistant',
          text: `Short, respectful, and specific — don't leak which offer won or the terms. Something like:

> Thanks for the strong offer on 88 Birch. After reviewing all three, Morgan has accepted another offer. We appreciated the clean terms and the effort your buyer put in — we'll keep you in mind if anything changes.

Do it fast (same day the acceptance goes out) so those agents can redeploy their buyer on the next listing. You want to stay on their good side for future deals.`,
        },
        {
          role: 'user',
          text: 'Anything else I should be thinking about before accepting?',
        },
        {
          role: 'assistant',
          text: `A few sanity checks — most of these don't need a doc:

- **Proof of funds / pre-approval depth.** A $15k gap is only worth what the buyer can actually cover. Make sure the lender letter reflects a real underwrite, not just a soft pull.
- **EM timing and amount.** How fast does it get deposited, and is it enough to hurt if they walk outside contingencies?
- **Buyer's agent reputation.** You've worked this market a long time — gut-check is often the most reliable signal on whether a deal actually closes.
- **Appraiser pool risk.** If recent comps around 88 Birch are thin, even a gap-protected offer can get wobbly on value.`,
        },
      ]
    case 'alex':
      return [
        {
          role: 'user',
          text: 'Walk me through what happens if Cedar closing slips past May 1.',
        },
        {
          role: 'assistant',
          text: `From **Contingent_Sale_Addendum_v3.docx** §3 the Elm close is tied to Cedar within a **7-day** window, so a short Cedar slip auto-extends Elm without amendments.

Beyond that window you're looking at written extensions on both sides, and Elm's rate lock per **FirstFederal_CTC_checklist.pdf** expires **May 12** — so drift past the first week or two starts to cost money.`,
        },
        {
          role: 'user',
          text: 'What does the Apr 29 –> May 1 window actually look like for the Parks day-to-day?',
        },
        {
          role: 'assistant',
          text: `This is the real risk on a back-to-back — not the lender mechanics, but **where the Parks sleep and where their stuff lives**.

Things worth confirming with them now:

- **Movers booked for the right day?** Same-day back-to-back often means a morning truck load at Cedar and an afternoon unload at Elm. If closings slip, movers need a fallback (storage truck overnight, flexible rescheduling window).
- **Cedar buyer and early possession.** Some Cedar buyers will let the Parks keep keys for 24–48 hours post-close in exchange for a use-and-occupancy agreement. That's a free safety net if Elm slips a day.
- **Hotel / short-term rental fallback.** Cheap insurance for a 1–3 night slip. Worth having a plan, not worth booking yet.
- **Utilities cutover.** Cedar on the close date, Elm live the same day — easy to miss if both sides assume the other side handled it.

Lenders usually work; logistics are what actually cause pain on contingent closes.`,
        },
        {
          role: 'user',
          text: 'What should we line up with title and both agents this week so May 1 feels smooth for the Parks?',
        },
        {
          role: 'assistant',
          text: `One thread, one timeline everyone can see:

- **Title** — confirm the sequence (Cedar first, Elm same day), wiring instructions, and who needs what signed by when.
- **Cedar buyer’s agent** — confirm walkthrough and any access the Parks need for movers; flag the target signing window.
- **Elm listing agent** — same for Elm walkthrough and signing; make sure they know Cedar is the same-day predecessor so no one schedules a surprise overlap.

Put the key dates in a single email (or shared doc) so nobody is working off voicemail. The goal is the Parks knowing *hour-by-hour* what May 1 looks like, not discovering conflicts the night before.`,
        },
        {
          role: 'user',
          text: 'Give me a clean checklist for the two weeks before close.',
        },
        {
          role: 'assistant',
          text: `Two-week run-up for a back-to-back:

1. **~T-14** — confirm Cedar payoff figures ordered; Elm CD draft requested.
2. **~T-10** — Alex picks moving date; buyer-side movers locked.
3. **~T-7** — Elm CD reviewed with Alex; final walkthrough window scheduled.
4. **~T-3** — wire instructions confirmed **by phone** with title (never off email).
5. **~T-1** — final walkthrough on Elm; utilities transfer queued for close date.
6. **Close day** — Cedar morning, Elm afternoon, keys in hand by evening.

Most of this is lining up so the Parks don't end up homeless for a night because something non-critical slipped.`,
        },
        {
          role: 'user',
          text: 'What changed in the redlined addendum v3?',
        },
        {
          role: 'assistant',
          text: `From **Re: Contingent addendum v3 redlined**, three edits in **Contingent_Sale_Addendum_v3.docx**:

| Edit | Stance |
| --- | --- |
| Kick-out shortened **72h → 48h** | **Push back** — 48h is thin if the back-up offer is soft |
| **Automatic EM release** on Cedar close | **Accept** — removes a real friction point |
| **5-day lender-delay cure** | **Accept** — protects the Parks if Cedar's payoff is slow |

Two accepts, one push back — low drama.`,
        },
      ]
    case 'sam':
      return [
        {
          role: 'user',
          text: 'Velocity says we’re clear to close except conditions 4401 and 4502. What do they actually need?',
        },
        {
          role: 'assistant',
          text: `From **Velocity Loans — final conditions (4401, 4502)**:

| # | Need | Fix |
| --- | --- | --- |
| **4401** | Updated paystub within **30** days of funding | Sam uploads latest from HR portal |
| **4502** | HOI binder effective date mismatch | Have carrier re-issue with the correct effective date |

Both are usually same-day once payroll and insurance pick up the phone.`,
        },
        {
          role: 'user',
          text: 'Is the CD clean against the original LE?',
        },
        {
          role: 'assistant',
          text: `Cash-to-close is up about **$1,847** vs **Loan_Estimate_original.pdf**:

| Line item | Δ | Read |
| --- | ---: | --- |
| County recording | **+$112** | Government fee — usually fine |
| Title endorsement | **+$285** | Not on the LE — worth asking Velocity to explain or absorb |
| Tax proration | **+$1,450** | Actual county figures — expected variance |

The **$285** endorsement is the one to push back on.`,
        },
        {
          role: 'user',
          text: 'Sam is getting nervous about the basement moisture. How should I coach him through this?',
        },
        {
          role: 'assistant',
          text: `This is more of a human moment than a tactical one — a few thoughts:

- **Normalize it.** Minor moisture on a final walkthrough is common, especially after wet weather. It's not a dealbreaker in itself.
- **Separate the decision.** Two questions, not one: *Is the house still the right house?* and *What's fair to ask for now that we've found this?* Most buyers conflate them when they're stressed.
- **Anchor to the move-in plan.** Sam wants to be in the house on the **Apr 24** close date — that's the real constraint. Asking for a small credit keeps the timeline intact; demanding remediation doesn't.
- **Give him a simple ask.** People handle negotiations better when they know exactly what you're requesting. "$1,500 credit, sign today, close Apr 24" is easier to sit with than "we're seeing what they'll agree to."

Call him, don't text this one — tone matters.`,
        },
        {
          role: 'user',
          text: 'What do I tell him about wire timing and fraud risk?',
        },
        {
          role: 'assistant',
          text: `Wire fraud is the single biggest preventable loss in residential real estate right now — worth being a little heavy-handed.

- Wire must hit escrow by **1pm local** the day before closing.
- Sam should initiate at his bank in the **morning** — domestic wires post same-day.
- **Most important:** he verbally confirms wiring instructions by calling title on the phone number from **their website**, not from any email — even emails that look like they came from me or from title.

Tell him: "If you get an email today or tomorrow with updated wire instructions, that's a fraud attempt. Don't act on it. Call me first."`,
        },
        {
          role: 'user',
          text: 'Give me a two-sentence text for Sam tonight.',
        },
        {
          role: 'assistant',
          text: `Client-facing text:

> Final stretch: lender needs a fresh paystub from your work portal today and a corrected insurance binder — I'm handling the binder with the carrier. Walkthrough found a bit of basement moisture, so I'm asking the seller for a **$1,500** credit at closing so we stay on track for **Apr 24**.

One action item for Sam, no alarm.`,
        },
        {
          role: 'user',
          text: 'Anything else I should be thinking about for a first-time buyer here?',
        },
        {
          role: 'assistant',
          text: `A few things first-time buyers often miss — none of this is about Sam's file specifically, just worth a mention before closing:

- **Utilities + mail forwarding.** Small, easy to forget, annoying when it isn't done.
- **Homestead / primary residence filings.** If his state offers a property tax exemption for primary residences, remind him to file once recorded.
- **Keep a closing folder.** CD, title policy, loan docs, HOI — he'll need them at tax time and any time he refinances.
- **Don't open new credit for 30 days.** Post-close rate refis or new cards can still cause ripples if Velocity funds late; easier to just wait.

Worth a 5-minute conversation the day before signing.`,
        },
      ]
    case 'taylor':
      return [
        {
          role: 'user',
          text: 'Buyer’s agent sent over their requested contract edits. What actually changed?',
        },
        {
          role: 'assistant',
          text: `From **Buyer_Requested_Edits.pdf** against the **Purchase_Agreement.pdf**, three things worth separating:

| # | Change | Stance |
| --- | --- | --- |
| 1 | Inspection timing shifted from calendar to **business days** | Minor — accept |
| 2 | Softer financing contingency language (“best efforts”) | **Push back** — this is the one that can cost you a close |
| 3 | Seller credit cap bumped to **$10k** | Economics only — negotiable |

The financing language is the real story; the rest is bargaining texture.`,
        },
        {
          role: 'user',
          text: 'Our counter #2 capped credits at $8k. They came back at $10k. Hold the line?',
        },
        {
          role: 'assistant',
          text: `The gap is $2k. On **Counter_Proposal_v2.docx** math that's roughly **$1,880** lighter net after commission and fees — real money, but not deal-defining.

**Buyer_Pre-approval_ValleyBank.pdf** shows Valley Bank at 5.875% with a 3% down-payment assistance program, which strongly suggests the buyer is using credits for **closing costs**, not to chip price. That's generally a good signal — they want to close, they just need the liquidity.

If Taylor doesn't feel strongly about the $2k, giving it often buys an executed contract tonight. If she does, hold at $9k and split the difference.`,
        },
        {
          role: 'user',
          text: 'Counter expires Apr 22 at 6pm. How do I work with Taylor on what to accept vs push back on?',
        },
        {
          role: 'assistant',
          text: `Treat this as **Taylor’s** call — your job is to lay out tradeoffs clearly, then help her draft whatever **she** wants to send.

**Typical split (she can mix and match)**

| Term | Often fine to concede | Often worth pushing back |
| --- | --- | --- |
| Credit cap **$10k** vs **$8k** | Small net difference (~**$2k**); many sellers take **$10k** to keep momentum | If Taylor is firm on net, counter **$9k** or hold **$8k** |
| Business-day inspection timing | Low risk, common ask | Rarely worth a fight |
| “Best efforts” financing | — | **Usually worth rejecting** — keeps the buyer’s obligation to close clear |

If Taylor is comfortable conceding on credit + timing but **not** on financing language, that’s a coherent package: **her** counter says yes on 1–2, no on 3, with a short fuse (e.g. 24 hours) so the buyer side responds in writing.`,
        },
        {
          role: 'user',
          text: 'Is there a downside to just accepting everything they asked for and moving on?',
        },
        {
          role: 'assistant',
          text: `The one piece worth flagging with Taylor is the **“best efforts”** financing language.

The rest is mostly timing and dollars — a few extra business days, a higher credit cap. That stuff rarely changes whether you get to the closing table. Softer financing wording can make it harder to hold the buyer to the same standard as the original contract if underwriting gets noisy.

So the conversation with Taylor isn’t “never concede” — it’s **which concessions trade for what**. Many sellers are fine with **$10k** + business-day timing and still want the **original** financing contingency locked in.`,
        },
        {
          role: 'user',
          text: 'If Taylor wants that package (yes on credit + timing, no on financing language), draft seller counter language she could send.',
        },
        {
          role: 'assistant',
          text: `Template only — Taylor should read it in her own voice and only send what she agrees with (fill dates):

> Seller's **Counter #3** to Buyer's requested edits dated **[date]**, reference **Purchase_Agreement.pdf**:
>
> 1. Seller accepts a closing cost credit cap of **$10,000** *(or substitute **$9,000** / **$8,000** if Taylor prefers)*.
> 2. Seller accepts business-day framing for inspection response timing.
> 3. Seller **does not accept** the proposed "best efforts" modification to the financing contingency — original financing contingency language controls.
> 4. All other terms unchanged. Counter expires **[date]** at 6:00 p.m. local.`,
        },
        {
          role: 'user',
          text: 'How should I talk this through with Taylor on the phone?',
        },
        {
          role: 'assistant',
          text: `Lead with questions, then recommendations:

1. **“What matters most to you on this deal — net walkaway, speed to close, or protecting yourself if financing wobbles?”** That tells you whether the **$2k** credit gap is worth a conversation.
2. **Walk the financing clause in plain English** — not “we’re rejecting their agent,” just “this wording softens what happens if their loan gets bumpy compared to what we already agreed to.”
3. **Offer two packages:** e.g. (A) concede **$10k** + business days, hold firm on financing; (B) same on financing, meet at **$9k** credit if she wants to split the difference.
4. **Close with:** “Whatever you pick, I’ll get the counter drafted tonight so we’re inside their deadline.”

You’re aligning on **her** risk tolerance — not deciding for her.`,
        },
      ]
    default:
      return []
  }
}

export default function LandingAppPreview() {
  const [activeId, setActiveId] = useState(CLIENTS[0].id)
  const client = useMemo(() => CLIENTS.find(c => c.id === activeId) ?? CLIENTS[0], [activeId])
  const turns = useMemo(() => threadForClient(client.id), [client.id])
  const chatScrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const el = chatScrollRef.current
    if (!el) return
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    el.scrollTo({ top: 0, behavior: reduce ? 'auto' : 'smooth' })
  }, [client.id])

  return (
    <div className="space-y-10">
      <div className="max-w-2xl">
        <h2
          id="preview-heading"
          className="font-landing-display text-3xl font-semibold tracking-tight text-brand-cloud sm:text-4xl"
        >
          App preview
        </h2>
        <p className="mt-3 text-sm leading-relaxed text-brand-cloud/55">
          Interactive mock: pick a client to load a sample thread. Assistant replies cite synced{' '}
          <strong className="text-brand-cloud/75">email</strong> subjects and{' '}
          <strong className="text-brand-cloud/75">documents</strong> the way the real app does.
        </p>
      </div>

      <div
        className="overflow-hidden rounded-2xl border border-white/10 bg-black/40 shadow-2xl ring-1 ring-white/5"
        role="region"
        aria-label="Reco workspace layout preview"
      >
        <div className="flex items-center gap-2 border-b border-white/5 bg-black/35 px-3 py-2">
          <span className="h-2.5 w-2.5 rounded-full bg-red-400/70" aria-hidden />
          <span className="h-2.5 w-2.5 rounded-full bg-amber-300/70" aria-hidden />
          <span className="h-2.5 w-2.5 rounded-full bg-emerald-400/60" aria-hidden />
          <span className="ml-2 font-mono text-[10px] text-brand-cloud/35">app / signed-in</span>
        </div>

        <div className="flex min-h-[440px] max-h-[min(62vh,600px)] text-[11px] font-sans leading-snug sm:min-h-[460px]">
          {/* Sidebar */}
          <div className="flex w-[min(44%,230px)] shrink-0 flex-col border-r border-white/5 bg-black/25 backdrop-blur-sm">
            <div className="shrink-0 border-b border-white/5 p-3">
              <div className="mb-2 flex items-center gap-2">
                <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-white/10 bg-gradient-to-br from-brand-navy to-brand-slate">
                  <span className="text-[10px] font-semibold tracking-tight text-brand-cloud">R</span>
                </div>
                <span className="truncate font-display text-sm font-semibold tracking-tight text-brand-cloud">Reco</span>
              </div>
              <div className="rounded-lg border border-white/10 bg-white/[0.05] py-1.5 text-center text-[10px] font-medium text-brand-cloud/70">
                + New Client
              </div>
            </div>
            <div className="min-h-0 flex-1 overflow-y-auto py-1" role="list" aria-label="Sample clients">
              {CLIENTS.map(c => {
                const isActive = c.id === activeId
                return (
                  <button
                    key={c.id}
                    type="button"
                    role="listitem"
                    onClick={() => setActiveId(c.id)}
                    aria-pressed={isActive}
                    className={`w-full border-l-2 px-3 py-2.5 text-left transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-mint/45 focus-visible:ring-offset-2 focus-visible:ring-offset-[#18181b] ${
                      isActive
                        ? 'border-brand-mint bg-white/[0.06]'
                        : 'border-transparent hover:bg-white/[0.03]'
                    }`}
                  >
                    <div className="flex items-center gap-1.5">
                      <span className={`flex-1 truncate text-[11px] ${isActive ? 'font-medium text-brand-cloud' : 'text-brand-cloud/80'}`}>
                        {c.name}
                      </span>
                      <span
                        className={`max-w-[5.2rem] shrink-0 truncate rounded-full px-1.5 py-0.5 text-[8px] font-medium uppercase tracking-wide ${clientTypeSidebarPillClass(c.type)}`}
                        title={c.type}
                      >
                        {c.type}
                      </span>
                    </div>
                    <p className="mt-0.5 text-[9px] text-brand-cloud/40">{c.dateLabel}</p>
                  </button>
                )
              })}
            </div>
          </div>

          {/* Chat */}
          <div className="flex min-w-0 flex-1 flex-col border-x border-white/5">
            <div className="shrink-0 border-b border-white/5 bg-black/20 px-4 py-2.5">
              <h3 className="text-[12px] font-semibold tracking-tight text-brand-cloud">{client.name}</h3>
              <p className="mt-0.5 text-[9px] uppercase tracking-[0.15em] text-brand-cloud/40">Reco Pilot</p>
            </div>
            <div
              ref={chatScrollRef}
              className="min-h-0 flex-1 space-y-3 overflow-y-auto overscroll-contain px-4 py-3 scroll-smooth"
              tabIndex={0}
              aria-label={`Sample conversation for ${client.name}`}
            >
              {turns.map((turn, idx) =>
                turn.role === 'user' ? (
                  <div key={idx} className="flex justify-end">
                    <div className="max-w-[90%] rounded-2xl rounded-br-sm bg-brand-mint px-3 py-2 text-[11px] font-medium leading-relaxed text-brand-navy">
                      {turn.text}
                    </div>
                  </div>
                ) : (
                  <div key={idx} className="flex justify-start">
                    <div className="mr-1.5 mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-lg border border-white/10 bg-gradient-to-br from-brand-navy to-brand-slate text-[9px] font-semibold tracking-tight text-brand-cloud">
                      R
                    </div>
                    <div className="min-w-0 max-w-[92%] rounded-2xl rounded-bl-sm border border-white/10 bg-white/[0.03] px-3 py-2 text-brand-cloud/90 backdrop-blur-sm">
                      <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        components={previewAssistantMarkdownComponents}
                      >
                        {normalizeChatMarkdown(turn.text)}
                      </ReactMarkdown>
                    </div>
                  </div>
                ),
              )}
              <p className="pb-1 text-center text-[9px] text-brand-cloud/35">Scroll for more · sample only</p>
            </div>
            <div className="shrink-0 border-t border-white/5 bg-black/20 px-3 py-2">
              <div className="flex items-end gap-1.5 rounded-lg border border-white/10 bg-white/[0.04] px-2 py-1.5 backdrop-blur-sm">
                <div className="flex-1 py-0.5 text-[10px] text-brand-cloud/35">Ask Reco about this client…</div>
                <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-brand-mint/50" aria-hidden>
                  <svg className="h-3 w-3 rotate-90 text-brand-navy/60" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M2 21l21-9L2 3v7l15 2-15 2v7z" />
                  </svg>
                </div>
              </div>
            </div>
          </div>

          {/* Right column — context sources */}
          <div className="hidden w-[min(40%,252px)] shrink-0 flex-col border-l border-white/5 bg-black/20 backdrop-blur-sm md:flex">
            <div className="max-h-full min-h-0 flex-1 overflow-y-auto p-3">
              <p className="mb-2 text-[9px] font-semibold uppercase tracking-[0.15em] text-brand-mint/70">In context</p>

              <button type="button" className="mb-1 flex w-full items-center justify-between group" tabIndex={-1}>
                <span className="text-[9px] font-semibold uppercase tracking-[0.15em] text-brand-cloud/55 group-hover:text-brand-cloud">
                  Active transaction
                </span>
                <span className="text-[10px] text-brand-cloud/35">▲</span>
              </button>
              <div className="rounded-lg border border-white/10 bg-white/[0.03] p-2">
                <p className="truncate text-[10px] font-medium text-brand-cloud">{client.propertyLine}</p>
                <p className="mt-1 text-[10px] text-brand-cloud/55">{client.offerLine}</p>
                <div className="mt-2 space-y-1">
                  {client.keyDates.map(kd => (
                    <div
                      key={kd.label}
                      className={`flex items-center justify-between rounded px-1.5 py-1 ${
                        kd.urgent
                          ? 'border border-orange-400/30 bg-orange-400/10'
                          : 'border border-white/5 bg-white/[0.03]'
                      }`}
                    >
                      <span className="text-[9px] text-brand-cloud/90">{kd.label}</span>
                      <span className={`text-[9px] shrink-0 ${kd.urgent ? 'font-medium text-orange-200' : 'text-brand-cloud/50'}`}>
                        {kd.date}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              <button type="button" className="mt-4 mb-1 flex w-full items-center justify-between group" tabIndex={-1}>
                <span className="text-[9px] font-semibold uppercase tracking-[0.15em] text-brand-cloud/55">Email sync</span>
                <span className="text-[10px] text-brand-cloud/35">▲</span>
              </button>
              <p className="mb-2 rounded border border-white/5 bg-white/[0.02] px-2 py-1.5 text-[9px] leading-snug text-brand-cloud/50">
                Threads involving <span className="text-brand-cloud/75">{client.gmailLine}</span> are indexed into this
                workspace.
              </p>
              <ul className="space-y-1.5">
                {client.emailThreads.map(t => (
                  <li
                    key={t.subject}
                    className="rounded border border-white/8 bg-black/25 px-2 py-1.5 text-[9px] text-brand-cloud/60"
                  >
                    <p className="font-medium text-brand-mint/90 line-clamp-2">{t.subject}</p>
                    <p className="mt-0.5 line-clamp-2 text-brand-cloud/45">{t.preview}</p>
                  </li>
                ))}
              </ul>

              <button type="button" className="mt-4 mb-1 flex w-full items-center justify-between group" tabIndex={-1}>
                <span className="text-[9px] font-semibold uppercase tracking-[0.15em] text-brand-cloud/55">Documents</span>
                <span className="text-[10px] text-brand-cloud/35">▲</span>
              </button>
              <ul className="space-y-1">
                {client.documents.map(doc => (
                  <li
                    key={doc}
                    className="truncate rounded border border-white/5 px-1.5 py-1 font-mono text-[9px] text-brand-cloud/65"
                  >
                    {doc}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <div
          className="rounded-2xl border border-white/10 bg-black/35 p-4 font-sans shadow-lg ring-1 ring-white/5"
          role="region"
          aria-label="Why email and files matter"
        >
          <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.15em] text-brand-cloud/45">Why it feels grounded</p>
          <p className="text-[11px] leading-relaxed text-brand-cloud/60">
            Reco builds prompts from the same objects you see in the right rail: message subjects from synced email, file names from
            folder sync and uploads, plus deal dates. The assistant is nudged to <strong className="text-brand-cloud/80">name those sources</strong> when it reasons — so you can
            verify fast.
          </p>
        </div>
        <div
          className="rounded-2xl border border-white/10 bg-black/35 p-4 font-sans shadow-lg ring-1 ring-white/5"
          role="region"
          aria-label="Try the preview"
        >
          <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.15em] text-brand-cloud/45">Try it here</p>
          <p className="text-[11px] leading-relaxed text-brand-cloud/60">
            Click another client in the sidebar — each has a longer sample thread you can <strong className="text-brand-cloud/80">scroll inside the chat pane</strong>. On
            smaller screens the context column hides; widen the window to see email and documents alongside the thread.
          </p>
        </div>
        <div
          className="rounded-2xl border border-white/10 bg-black/35 p-4 font-sans shadow-lg ring-1 ring-white/5 md:col-span-2"
          role="region"
          aria-label="Custom AI system prompts"
        >
          <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.15em] text-brand-cloud/45">Custom system prompts</p>
          <p className="text-[11px] leading-relaxed text-brand-cloud/60">
            After sign-in, open <strong className="text-brand-cloud/80">AI prompt settings</strong> from your profile menu
            to override the assistant’s system prompt separately for{' '}
            <strong className="text-brand-cloud/80">buyer</strong>, <strong className="text-brand-cloud/80">seller</strong>,
            and <strong className="text-brand-cloud/80">{'buyer & seller'}</strong> workspaces. Use it to steer negotiation
            style—more collaborative or more direct—how concise replies should be, and when to lean on synced email and
            documents versus general advice. Reset to defaults anytime.
          </p>
        </div>
      </div>
    </div>
  )
}
