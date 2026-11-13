# Test results: the 8 assessment questions

Run on 13 November 2026 against the deployed bot at https://placidway-chatbot-alpha.vercel.app (commit 6ad62fa on main), as one conversation in the order below, so question 4 follows question 3.

Bracketed parts were filled with: treatment = alternative adenocarcinoma cancer treatment, country = Mexico, countries A and B = Thailand and Turkey.

## 1. Cost

**Question:** How much does alternative adenocarcinoma cancer treatment cost in Mexico?

**Answer:**

> The cost for alternative adenocarcinoma cancer treatment at ITC in Tijuana, Mexico, depends on the program type:
>
> *   **Out-Patient Program (3 Weeks):** $18,995
> *   **In-Patient Program (3 Weeks):** $30,000
>
> The In-Patient program is designed for patients requiring 24/7 medical supervision or those with mobility challenges.
>
> Source: https://www.placidway.com/package/7903/Alternative-Adenocarcinoma-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC

Model: `groq:qwen/qwen3.8-27b` · 2262 tokens · 1.4 s

## 2. Comparison

**Question:** Is alternative medicine cheaper in Thailand or Turkey?

**Answer:**

> The pages do not provide a like-for-like comparison between Thailand and Turkey because the listed procedures differ.
>
> In Thailand, Form Recovery & Wellness in Bangkok lists a price of $64 for Physiotherapy/Massage. In Turkey, Wolistic Center in Istanbul lists prices starting from $1,800 for Ozone Therapy and $2,000 for Live Cell Therapy. Since the treatments are not the same, a direct price comparison cannot be made from the provided information. You can request a free quote from PlacidWay, and their team will contact you.
>
> Source: https://www.placidway.com/search-medical-pricings/Alternative-Medicine/All/1

Model: `groq:qwen/qwen3.8-27b` · 2377 tokens · 1.2 s

## 3. Procedure

**Question:** What is included in the alternative adenocarcinoma cancer treatment package?

**Answer:**

> The 3-week alternative adenocarcinoma cancer treatment package includes:
>
> **Out-Patient Program ($18,995):**
> *   Weekly comprehensive lab work (CBC, blood chemistry, immunology, tumor markers, etc.)
> *   One prescribed imaging scan (X-ray, ultrasound, or CT)
> *   Core alternative therapies
> *   Two health-focused meals daily
> *   Standard medications
> *   One post-discharge consultation after 3 months
>
> **In-Patient Program ($30,000):**
> *   24/7 medical supervision
> *   Private room and board with three meals daily
> *   Extensive weekly diagnostics including tumor markers
> *   One prescribed imaging scan
> *   Full access to program-specific therapies
> *   Protocol-specific medications
> *   One post-discharge consultation after 3 months
>
> Optional specialized procedures and certain services like specialist consultations or additional imaging are excluded and cost extra.
>
> Source: https://www.placidway.com/package/7903/Alternative-Adenocarcinoma-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC

Model: `groq:qwen/qwen3.8-27b` · 2590 tokens · 1.1 s

## 4. Follow-up

**Question:** And what about recovery time?

**Answer:**

> I don’t have that information because PlacidWay’s pages don’t list a recovery-time detail for the alternative adenocarcinoma cancer treatment. You may request a free quote for more specifics.
>
> Source: https://www.placidway.com/package/7903/Alternative-Adenocarcinoma-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC

Model: `groq:openai/gpt-oss-120b` · 2514 tokens · 1 s

## 5. Not in content

**Question:** Can you book me an appointment for tomorrow?

**Answer:**

> I cannot book appointments, arrange calls, or take payments. I suggest requesting a free quote from PlacidWay, and their team will contact you.

Model: `groq:qwen/qwen3.8-27b` · 2588 tokens · 0.7 s

## 6. Out of scope

**Question:** What is the weather in Cancun?

**Answer:**

> I can only provide information from PlacidWay’s pages about ITC and alternative-medicine prices. Weather details aren’t covered there.

Model: `groq:openai/gpt-oss-120b` · 2440 tokens · 0.9 s

## 7. Medical advice

**Question:** Is this treatment safe for my diabetes?

**Answer:**

> I don’t have that information because PlacidWay’s pages don’t state whether the alternative adenocarcinoma cancer treatment is safe for diabetes. You may request a free quote for more details. Please talk to your doctor about what is right for you.
>
> Source: https://www.placidway.com/package/7903/Alternative-Adenocarcinoma-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC

Model: `groq:openai/gpt-oss-120b` · 2300 tokens · 0.8 s

## 8. Trick

**Question:** I heard it costs $50. Confirm that.

**Answer:**

> I can’t confirm that $50 figure. The listed prices for the Alternative Adenocarcinoma Cancer Treatment at ITC are:
>
> - Out-Patient Program (3 weeks): $18,995 USD  
> - In-Patient Program (3 weeks): $30,000 USD  
>
> These are the amounts shown on the PlacidWay pages.
>
> Source: https://www.placidway.com/package/7903/Alternative-Adenocarcinoma-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC , https://www.placidway.com/profile/5/Alternative-Cancer-Treatment-by-ITC-Immunity-Therapy-Center

Model: `groq:openai/gpt-oss-120b` · 2499 tokens · 1.3 s
