import type { FaqRecord } from "@/lib/api";

export const faqSeeds: FaqRecord[] = [
  {
    id: "seed-1",
    question: "How do I access the content library?",
    answer:
      "Click Open Content Portal on the dashboard to access the BVIRAL library. You can search through the library, browse categories, and filter videos directly on the portal. Please only share videos on your approved channels.",
    category: "Library",
    is_published: true,
    display_order: 10,
  },
  {
    id: "seed-2",
    question: "Can I add or remove channels from my subscription?",
    answer:
      "Yes. Contact sales@bviral.com with your request and include the URLs for any channels you want to add or remove.",
    category: "Channels",
    is_published: true,
    display_order: 20,
  },
  {
    id: "seed-3",
    question: "How does billing work?",
    answer:
      "Depending on your selections at checkout, you will be billed monthly or annually. You can review billing details from the Manage Subscription page.",
    category: "Billing",
    is_published: true,
    display_order: 30,
  },
  {
    id: "seed-4",
    question: "What happens if I cancel my subscription?",
    answer:
      "You may keep the videos shared during your active subscription period, but you may not post new BVIRAL videos after your term ends. Email sales@bviral.com at least 30 days before the end of your term if you want to cancel.",
    category: "Billing",
    is_published: true,
    display_order: 40,
  },
  {
    id: "seed-5",
    question: "What if my channel username changed?",
    answer:
      "Contact sales@bviral.com immediately with your old and new usernames so the whitelist can be updated.",
    category: "Channels",
    is_published: true,
    display_order: 50,
  },
];
