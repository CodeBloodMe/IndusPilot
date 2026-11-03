# IndusPilot Multilingual Supplier Communication Specification

## 1. Context & Objectives

Industrial procurement in India operates across a diverse linguistic and cultural spectrum. While formal legal RFPs are often drafted in standard commercial English, regional manufacturing clusters (e.g. Pune-Pimpri-Chinchwad, Peenya-Bengaluru, Coimbatore, Ludhiana, Faridabad) heavily utilize Hindi and conversational Hinglish for rapid supplier negotiation.

The IndusPilot Supplier Communication Engine supports three tailored communication modes:
1. **Commercial English (`en`):** Structured, formal RFP format with reference numbers, delivery schedules, and clear benchmark rationale.
2. **Industrial Hindi (`hi`):** Formal Hindi register suited for North Indian industrial corridors with professional respect-markers (*Ji*, *Kripya*, *Dhanyawad*).
3. **Indian Trade Hinglish (`hinglish`):** High-velocity, relationship-driven commercial vernacular standard across Indian MSME trade desks.

---

## 2. Tone Guidelines & Cultural Etiquette

To maintain high response rates and preserve supplier relationships:
- **Respectful Professionalism:** Acknowledge past delivery reliability and existing supplier standing before introducing counteroffer terms.
- **Fact-Based Rationale:** Never make arbitrary "lowball" demands without citing commercial levers (e.g., aggregate batch volume, current market index, prompt cash payment terms).
- **Clear Call to Action (CTA):** Specify exact target price (₹/kg or ₹/unit), desired response timeline (typically 48 hours), and prompt payment commitments.
- **Human Accountability:** Messages close with the name and designation of the human commercial officer responsible for the account.

---

## 3. Communication Templates by Strategy

### 3.1 Strategy 1: Volume Commitment (`VOLUME_COMMITMENT`)

#### English (`en`)
```text
Ref: INDUS-NEG/2026/001 - Request for Volume Pricing Revision

Dear Apex Steel & Alloys Pvt Ltd Team,

Thank you for your quotation regarding 800.0 kg of Stainless Steel 304 Sheet Plate at Rs. 315.00/kg.

Our production schedule requires a consolidated order volume of 800.0 kg. In light of this substantial batch quantity, which represents a significant order for our manufacturing cycle, we respectfully request a revised price of Rs. 295.00/kg (approx. 6.35% concession).

We can confirm prompt payment terms (15 Days Prompt Net) upon mutual agreement on this rate. Please confirm your updated commercial terms within 48 hours.

Sincerely,
Procurement Officer, IndusPilot Manufacturing
```

#### Hindi (`hi`)
```text
विषय: ऑर्डर संदर्भ INDUS-NEG/2026/001 - वॉल्यूम डिस्काउंट हेतु मूल्य समीक्षा

नमस्ते Apex Steel & Alloys Pvt Ltd टीम,

800.0 kg Stainless Steel 304 Sheet Plate के लिए आपके कोटेशन (Rs. 315.00/kg) के लिए धन्यवाद।

हमारा वर्तमान प्रोडक्शन बैच 800.0 kg की बड़ी मात्रा की मांग करता है। इस महत्वपूर्ण वॉल्यूम को ध्यान में रखते हुए, हम आपसे Rs. 295.00/kg के संशोधित दर का विनम्र अनुरोध करते हैं।

इस दर पर सहमति होने पर हम 15 Days Prompt Net के तहत समय पर भुगतान सुनिश्चित करेंगे। कृपया 48 घंटों में अपना संशोधित कोटेशन साझा करें।

धन्यवाद,
प्रोक्योरमेंट टीम, IndusPilot
```

#### Hinglish (`hinglish`)
```text
Subject: Commercial Price Negotiation - Apex Steel & Alloys Pvt Ltd - Volume Order

Dear Apex Steel & Alloys Pvt Ltd Team,

Aapka quote mila for 800.0 kg Stainless Steel 304 Sheet Plate at Rs. 315.00/kg.

Hamara immediate requirement 800.0 kg ka bulk batch hai. Market volume benchmark aur is regular quantity ko consider karte hue, hum target rate Rs. 295.00/kg propose kar rahe hain.

Agar aap ye rate match karte hain, toh hum 15 Days Prompt Net terms par order immediately release kar denge. Please review karke revised rate confirm karein.

Best regards,
Procurement Team, IndusPilot
```

---

## 4. Inbound Supplier Response Extraction Engine

When a supplier responds (via email, WhatsApp, or simulated testing), the engine applies deterministic regex extraction combined with sentiment classification:
- **Price Extraction:** Matches numerical rates preceding or succeeding `Rs.`, `₹`, `/kg`, `/unit`, `INR`.
- **Classification:**
  - `CONCESSION`: Supplier offered a lower price than opening.
  - `ACCEPTANCE`: Supplier accepted buyer's exact target price.
  - `COUNTER`: Supplier offered an intermediate split price.
  - `FIRM`: Supplier maintained initial quoted price.
  - `REJECTION`: Supplier declined to negotiate or cannot fulfill.
- **Immediate Landed Cost Recalculation:** The newly extracted unit price is automatically piped into `calculate_landed_cost()`.

