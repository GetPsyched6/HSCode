import base64
import json
import re
import requests
from typing import Dict, Any
from app.core import config


class WatsonxHSCodeClassifier:
    """Watsonx client for HS code classification using vision model"""

    def __init__(self):
        self.api_key = config.WATSONX_API_KEY
        self.project_id = config.WATSONX_PROJECT_ID
        self.url = config.WATSONX_URL
        self.access_token = None

    def get_access_token(self, force_refresh: bool = False) -> str:
        """Get access token for Watsonx API"""
        if self.access_token and not force_refresh:
            return self.access_token

        auth_url = "https://iam.cloud.ibm.com/identity/token"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }
        data = {
            "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
            "apikey": self.api_key,
        }

        response = requests.post(auth_url, headers=headers, data=data)
        if response.status_code == 200:
            self.access_token = response.json()["access_token"]
            return self.access_token
        else:
            raise Exception(f"Failed to get access token: {response.text}")

    def encode_image(self, image_path: str) -> str:
        """Encode image to base64 string"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    def _apply_smart_hs_matching(self, ai_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply Python-level logic to match HS codes based on AI's visual analysis.
        This overrides obviously wrong AI decisions.
        """
        try:
            # Extract visual characteristics from AI
            visual_analysis = ai_result.get("visual_analysis", {})
            color = visual_analysis.get("color", "").lower()
            processing_state = visual_analysis.get("processing_state_observed", "").lower()
            
            # Get AI's classification attempt
            classifications = ai_result.get("classifications", [])
            if not classifications:
                return ai_result
            
            # Check each classification
            for classification in classifications:
                hs_code = classification.get("hs_code", "")
                description = classification.get("article_description", "").lower()
                
                # FIRST: Check if AI embedded suffix in hs_code (e.g., "0901.21.00.65")
                # We need hs_code to ONLY be 3 parts, suffix goes in stat_suffix
                parts = hs_code.split(".")
                if len(parts) >= 4 and parts[3].isdigit():
                    # AI included suffix in hs_code - extract it!
                    extracted_suffix = parts[3]
                    base_hs_code = ".".join(parts[:3])
                    classification["hs_code"] = base_hs_code
                    # Only set stat_suffix if it's empty or not already numeric
                    if not classification.get("stat_suffix", "").replace(".", "").isdigit():
                        classification["stat_suffix"] = extracted_suffix
                    print(f"⚠️  AI embedded suffix in HS code - extracted {extracted_suffix}, base code: {base_hs_code}")
                    hs_code = base_hs_code  # Update for further processing
                
                # CRITICAL VALIDATION: Check for obvious mismatches
                is_dark_color = any(word in color for word in ["brown", "black", "dark", "dried", "charred"])
                is_light_color = any(word in color for word in ["green", "light", "pale", "fresh", "raw", "white"])
                
                is_processed_visual = any(word in processing_state for word in ["processed", "roasted", "cooked", "dried", "fermented"])
                is_unprocessed_visual = any(word in processing_state for word in ["unprocessed", "raw", "fresh", "not roasted", "not fermented"])
                
                # Check if HS code description contradicts visual observation
                has_processed_code = any(word in description for word in ["roasted", "processed", "cooked", "fermented", "dried"])
                has_unprocessed_code = any(word in description for word in ["not roasted", "not processed", "not fermented", "raw", "fresh"])
                
                # OVERRIDE LOGIC: If color/processing says one thing but code says another
                if (is_dark_color or is_processed_visual) and has_unprocessed_code:
                    print(f"🔧 PYTHON OVERRIDE: Visual analysis shows processed/dark ({color}, {processing_state}) but AI picked 'not roasted/processed' code. Looking for correct code...")
                    
                    # Try to find the correct "roasted/processed" version of this code
                    if "0901.11" in hs_code:  # Not roasted coffee
                        # Switch to roasted version
                        # IMPORTANT: When changing category, we MUST use the default "Other" suffix for the NEW category
                        # Suffixes are category-specific! Don't copy suffix from "not roasted" to "roasted"
                        classification["hs_code"] = "0901.21.00"
                        classification["stat_suffix"] = "49"  # Default "Other: Other" for roasted category
                        classification["article_description"] = "Coffee, roasted: Not decaffeinated: In retail containers weighing 2 kg or less: Other: Other"
                        print(f"   → Corrected to 0901.21.00 with suffix 49 (roasted, Other: Other)")
                        
                        # Update reasoning
                        classification["reasoning"] = f"The product exhibits a dark brown color and processed appearance, indicating it has been roasted. The packaging does not display organic certification marks or specific variety text, so the general Other suffix is applied within the roasted coffee category. (AI guidance corrected by system validation)"
                        
                        # VALIDATE & FIX product_description too
                        prod_desc = classification.get("product_description", "").lower()
                        if any(word in prod_desc for word in ["unprocessed", "not roasted", "raw", "green"]):
                            # Product description contradicts the corrected state
                            classification["product_description"] = classification.get("product_description", "").replace("unprocessed", "processed").replace("not roasted", "roasted").replace("raw", "roasted").replace("green", "dark brown roasted")
                            print(f"   → Also corrected product_description to match roasted state")
                
                elif (is_light_color or is_unprocessed_visual) and has_processed_code:
                    print(f"🔧 PYTHON OVERRIDE: Visual analysis shows unprocessed/light ({color}, {processing_state}) but AI picked 'roasted/processed' code. Looking for correct code...")
                    
                    # Try to find the correct "not roasted/processed" version
                    if "0901.21" in hs_code:  # Roasted coffee
                        # Switch to not roasted version
                        # IMPORTANT: When changing category, we MUST use the default "Other" suffix for the NEW category
                        # Suffixes are category-specific! Don't copy suffix from "roasted" to "not roasted"
                        classification["hs_code"] = "0901.11.00"
                        classification["stat_suffix"] = "65"  # Default "Other: Other" for not roasted category
                        classification["article_description"] = "Coffee, not roasted: Not decaffeinated: Other: Other"
                        print(f"   → Corrected to 0901.11.00 with suffix 65 (not roasted, Other: Other)")
                        
                        # VALIDATE & FIX product_description too
                        prod_desc = classification.get("product_description", "").lower()
                        if any(word in prod_desc for word in ["processed", "roasted", "cooked", "dried", "dark"]):
                            # Product description contradicts the corrected state
                            classification["product_description"] = classification.get("product_description", "").replace("processed", "unprocessed").replace("roasted", "not roasted").replace("cooked", "raw").replace("dark brown", "light green")
                            print(f"   → Also corrected product_description to match not roasted state")
                        
                        # Update reasoning
                        classification["reasoning"] = f"The product exhibits a light/green color and unprocessed appearance, indicating it is not roasted. The packaging does not display organic certification marks or specific variety text, so the general Other suffix is applied within the not roasted category. (AI guidance corrected by system validation)"
            
            return ai_result
            
        except Exception as e:
            print(f"⚠️ Error in smart HS matching: {e}")
            # Return original result if validation fails
            return ai_result

    def classify_hs_code(self, image_path: str, retry_count: int = 0, max_retries: int = 2) -> Dict[str, Any]:
        """Classify product image to HS code using Watsonx Vision API
        
        Args:
            image_path: Path to the image file
            retry_count: Current retry attempt (internal use)
            max_retries: Maximum number of retries for non-JSON responses
        """

        try:
            # Get access token
            access_token = self.get_access_token()

            # Encode the image
            image_base64 = self.encode_image(image_path)

            # Build the prompt with HS code document
            prompt = f"""OUTPUT FORMAT: You MUST respond with ONLY a JSON object. Start your response immediately with {{ and end with }}. 

FORBIDDEN: Do NOT write "Answer:", "**Answer:**", "Here is", "JSON:", markdown code blocks (```), or ANY text outside the JSON object.

REQUIRED: Your entire response must be valid JSON that can be parsed by json.loads().

---

You are an expert customs classifier with deep knowledge of the Harmonized System (HS) codes and product identification.

**TASK: Analyze this product image and determine ALL POSSIBLE HS codes from the document below, ranked by confidence.**

HS CODE REFERENCE DOCUMENT:
{config.HS_CODE_DOCUMENT}

**CLASSIFICATION PROCESS - YOU MUST FOLLOW IN ORDER:**

⚠️⚠️⚠️ CRITICAL TWO-STEP PROCESS - THESE ARE SEPARATE ⚠️⚠️⚠️

STEP A: VISUAL APPEARANCE → MAIN CODE CATEGORY (FIRST 4-6 DIGITS)
Look at COLOR and PHYSICAL STATE only:
• Brown/black/dried/cooked → Pick codes starting with "roasted"/"processed"/"fermented"
• Light/green/pale/fresh/raw → Pick codes starting with "not roasted"/"raw"/"unprocessed"

STEP B: LABEL TEXT → SUFFIX (LAST 2 DIGITS)
Look at text/marks on packaging:
• Found "ORGANIC" text or seal → Use "Certified organic" suffix
• Found specific variety text → Use that variety's suffix  
• No special text found → Use "Other" suffix

DO NOT CONFUSE THESE STEPS:
❌ WRONG: "No label text, so I'll use 'not roasted'" 
✅ CORRECT: "Dark color = roasted code. No variety text = Other suffix."

VISUAL EXAMPLES (STEP A determines main code):
• Dark brown beans → "roasted" code | Light green beans → "not roasted" code
• Black tea leaves → "fermented" code | Green tea leaves → "not fermented" code  
• Dried fruit (dark/shriveled) → "dried" code | Fresh fruit (bright) → "fresh" code
• Cooked vegetables (dark) → "cooked/prepared" code | Raw vegetables (bright) → "raw" code
Then STEP B uses label text for suffix within that category.

═══════════════════════════════════════════════════════════════════════
PHASE 1: LABEL TEXT EXTRACTION (Complete this FIRST - MANDATORY)
═══════════════════════════════════════════════════════════════════════

Before making ANY classification decisions, you must extract information from the label:

1. **Read ALL visible text** on the product label/packaging (brand names, product names, descriptions, weight, etc.)
2. **Identify certification seals/logos** - Look for actual certification marks (USDA Organic seal, Fair Trade logo, certification body logos)
3. **List regulatory marks** - Any certification numbers, approval codes, or regulatory stamps
4. **Extract qualifier keywords** - Words that indicate specific product attributes: ORGANIC, CERTIFIED, specific varieties or grades, processing methods (DECAF, FLAVORED), material types, etc.

**CRITICAL RULES for label_text_extraction:**
- "visible_text": List EVERY word/phrase you can actually read on the packaging
- "certification_marks": List ONLY official certification seals/logos you can see (e.g., "USDA Organic seal visible", "Fair Trade logo")
  * If you see decorative flowers/leaves but NO certification seal → certification_marks: []
  * Decorative imagery is NOT a certification mark
- "qualifier_keywords": List ONLY explicit qualifier words you can READ on the label
  * If you see green colors but NO "ORGANIC" text → qualifier_keywords: []
  * Do NOT infer keywords from imagery, colors, or design
  * Only include words that are actually printed on the label
- "regulatory_marks": List any certification numbers or approval codes visible

**EXAMPLE of correct extraction:**
- Packaging with decorative design but no certification text → certification_marks: [], qualifier_keywords: []
- Packaging with "USDA Organic" seal visible → certification_marks: ["USDA Organic seal"], qualifier_keywords: ["ORGANIC"]
- Packaging with specific variety/grade text → qualifier_keywords: ["<variety name>", "<grade>"]

═══════════════════════════════════════════════════════════════════════
PHASE 2: HS CODE SELECTION (Use ONLY Phase 1 results)
═══════════════════════════════════════════════════════════════════════

Now classify using ONLY the text/marks you extracted in Phase 1.

**CRITICAL ANALYSIS REQUIREMENTS:**

1. **VISUAL INSPECTION** - Look carefully at EVERY detail:
   - Color, shade, and tone of the product (BE PRECISE - dark brown vs light brown vs green vs white, etc.)
   - Physical state (whole, ground, powder, leaves, liquid, solid)
   - Processing indicators - Base ONLY on visible evidence:
     * Dark brown/black/charred appearance → roasted/cooked/processed
     * Light/pale/green/raw appearance → unprocessed/raw/unroasted
     * Dried, shriveled, or desiccated texture → dried/dehydrated
     * Fermented, bloated, or cultured appearance → fermented
     * Ground/powdered form → processed/milled
     * DO NOT contradict what you visually observe - if it looks processed, it IS processed
   - Packaging (retail containers, bulk, bags, boxes, labels)
   - Size, shape, texture, and physical characteristics

2. **PRODUCT IDENTIFICATION** - Determine:
   - Base product category (what is it fundamentally?)
   - Processing or preparation state (raw, processed, cooked, fermented, etc.)
   - Variety, species, or type (ONLY if confirmed in Phase 1 extraction)
   - Special attributes (ONLY if confirmed in Phase 1 extraction)
   - Packaging type, size, and retail/bulk format

3. **HS CODE MATCHING** - Use the document systematically:
   
   **STEP 1: Understand HS Code Structure**
   HS codes are HIERARCHICAL. Read descriptions left-to-right:
   - BEGINNING of description = Major category (processing state, product type, fermentation)
   - MIDDLE of description = Physical characteristics (packaging, form, size)
   - END of description = Specific qualifiers (varieties, certifications)
   
   **STEP 2: Match by VISUAL Attributes First**
   Filter codes by what you can SEE:
   
   VISUAL ATTRIBUTES (observable, no label text needed):
   - Processing state: "roasted" vs "not roasted", "fermented" vs "not fermented", "cooked" vs "raw"
   - Physical form: whole/ground/powder/liquid
   - Color: brown/green/white/black (indicates processing)
   - Packaging: bulk/retail containers, size visible
   - Texture: dried/fresh, whole/milled
   
   → If you SEE a processed state → ONLY consider codes that say that state in the description
   → If you SEE an unprocessed state → ONLY consider codes that say that state in the description
   → Visual evidence IS proof - match it to the beginning/middle of HS descriptions
   
   **STEP 3: Match by LABEL Attributes**
   For codes with qualifiers at the END of descriptions:
   
   LABEL-DEPENDENT ATTRIBUTES (not observable, need text/marks):
   - Certifications: "Certified organic", "Fair trade"
   - Specific varieties: named varieties, grades, species
   - Decaffeinated status
   - Flavoring (when not visually obvious)
   
   → ONLY use specific qualifier codes if you found explicit text/marks in Phase 1
   → Otherwise use "Other" suffix
   
   Acceptable evidence:
   * Explicit text on label
   * Official certification seals/logos
   * Regulatory marks
   
   NOT acceptable:
   * Decorative imagery
   * Package color
   * Assumptions
   
   **STEP 4: MANDATORY VALIDATION**
   Before finalizing, re-read your selected code's FULL description:
   - Does the BEGINNING match what you SEE? (processing state)
   - Does the MIDDLE match what you SEE? (packaging, form)
   - Does the END match what the LABEL says? (qualifiers)
   → If ANY part doesn't match, select a different code

   **EVIDENCE-BASED CLASSIFICATION HIERARCHY:**
   When multiple codes differ by qualifiers:
   
   a) MANDATORY VALIDATION RULE - Cross-check with Phase 1:
      For codes with qualifiers (organic, decaf, specific variety), you MUST verify:
      
      ** To use "Certified organic" suffix codes:
         - REQUIRE: "ORGANIC" or "CERTIFIED ORGANIC" in label_text_extraction.qualifier_keywords
         - OR: "USDA Organic" or similar in label_text_extraction.certification_marks
         - If NEITHER exists → MUST use "Other" suffix
      
      ** To use "Arabica" or "Robusta" variety codes:
         - REQUIRE: "ARABICA" or "ROBUSTA" in label_text_extraction.qualifier_keywords
         - If NOT in qualifier_keywords → MUST use general variety code
      
      ** To use "Decaffeinated" codes:
         - REQUIRE: "DECAF" or "DECAFFEINATED" in label_text_extraction.qualifier_keywords
         - If NOT in qualifier_keywords → MUST use "Not decaffeinated" code
      
      ** To use "Flavored" codes:
         - REQUIRE: "FLAVORED" or specific flavor names in label_text_extraction.qualifier_keywords
         - If NOT in qualifier_keywords → MUST use non-flavored code
      
      **RULE: If the qualifier does NOT appear in label_text_extraction → use the general/"Other" classification**
   
   d) DEFAULT TO GENERAL:
      - If the distinguishing attribute is NOT in label_text_extraction → use the general/"Other" classification
      - If you cannot confirm a specific qualifier in Phase 1 results → do not use that specific code
      - Example: qualifier_keywords: [] and certification_marks: [] → use "Other" suffix, not "Certified organic" suffix
   
   e) RANKING PRIORITY:
      - General code with strong evidence > Specific code without Phase 1 confirmation
      - Rank by: (1) Phase 1 extraction confirmation, (2) Evidence strength, (3) General codes as fallback

4. **CONFIDENCE SCORING** - Be rigorous and conservative:
   - 0.9-1.0: Absolutely certain, all key indicators match perfectly, strong visual evidence for any specific attributes
   - 0.7-0.9: Very confident, most indicators clearly match, specific attributes have visible confirmation
   - 0.5-0.7: Moderately confident, some uncertainty remains, limited evidence for specific attributes
   - 0.3-0.5: Low confidence, multiple possibilities exist, no evidence for specific qualifiers
   - 0.0-0.3: Very uncertain, essentially guessing, assumptions without evidence
   
   **HARSH PENALTY FOR ASSUMPTIONS:**
   - If you use a SPECIFIC code (with qualifiers) WITHOUT visible evidence of that qualifier → cap confidence at 0.4 maximum
   - If you assume attributes not visible in the image → reduce confidence by at least 0.3
   - Prefer higher-confidence general codes over lower-confidence specific codes

**OUTPUT SCHEMA - Return with label extraction FIRST:**

{{
  "label_text_extraction": {{
    "visible_text": [
      "List ALL readable text on packaging",
      "Brand name, product name, descriptions, weight, etc.",
      "Every word or phrase you can read"
    ],
    "certification_marks": [
      "List ONLY official certification seals/logos visible",
      "Examples: 'USDA Organic seal', 'Fair Trade Certified logo'",
      "If NO certification seals → empty array []"
    ],
    "regulatory_marks": [
      "List certification numbers, approval codes, regulatory stamps",
      "If NONE visible → empty array []"
    ],
    "qualifier_keywords": [
      "List ONLY explicit qualifier words READ on the label",
      "Examples: 'ORGANIC', 'CERTIFIED', specific varieties, grades, processing methods",
      "Do NOT infer from colors/imagery",
      "If NO qualifier text → empty array []"
    ]
  }},
  "classifications": [
    {{
      "hs_code": "specific HS code (e.g., 0901.21.00)",
      "stat_suffix": "statistical suffix if applicable",
      "article_description": "exact description from HS document",
      "product_description": "what you see in this specific image",
      "reasoning": "CRITICAL: Write ONLY in natural, professional English for customs officers - NO TECHNICAL NOTATION ALLOWED. Do NOT use: 'Phase 1', 'visible_text', 'certification_marks', 'qualifier_keywords', '[]', or any JSON field names. Use TWO-STEP logic: (1) Visual appearance determines MAIN CODE (processed vs unprocessed), (2) Label text determines SUFFIX (specific vs Other). Example: 'The product exhibits a dark brown, processed appearance, placing it in the processed/roasted category. The packaging does not display organic certification or specific variety designations, so the general Other suffix is applied within that category.'",
      "confidence_score": 0.0 to 1.0,
      "key_characteristics": [
        "list of observed characteristics that support this classification"
      ]
    }}
  ],
  "visual_analysis": {{
    "product_type": "primary product category",
    "color": "exact color/shade observed (be specific: dark brown, light green, white, black, etc.)",
    "processing_state_observed": "CRITICAL: Base ONLY on appearance. Dark/dried/cooked = processed. Light/fresh/raw = unprocessed. This determines MAIN CODE, NOT suffix.",
    "packaging": "packaging description if visible",
    "decorative_elements": "describe any decorative imagery (flowers, leaves, patterns) - separate from certifications",
    "label_text_summary": "brief summary referencing what was found/not found in label_text_extraction",
    "two_step_validation": "MANDATORY: (A) If color is dark/brown/black, MAIN HS code MUST start with 'roasted'/'processed'/'fermented'. (B) Suffix is determined by label text, NOT by visual appearance. State both validations."
  }},
  "not_in_document": false
}}

**EXAMPLE STRUCTURE - Processed product with no qualifier text:**
{{
  "label_text_extraction": {{
    "visible_text": ["<brand name>", "<weight/size>"],
    "certification_marks": [],  // No certification seals visible
    "regulatory_marks": [],
    "qualifier_keywords": []  // No qualifier keywords found on label
  }},
  "classifications": [
    {{
      "hs_code": "<PROCESSED_CATEGORY_CODE>",  // STEP A: Visual state = processed → use processed category code
      "stat_suffix": "<OTHER_SUFFIX>",  // STEP B: No label qualifiers → use Other suffix
      "article_description": "<exact description from HS document>",
      "reasoning": "The product exhibits a dark, processed appearance, placing it in the processed/roasted category. The packaging does not display certification marks or specific variety text, so the general Other suffix is applied within that category.",
      "confidence_score": <0.0-1.0 based on evidence strength>
    }}
  ],
  "visual_analysis": {{
    "processing_state_observed": "Processed (dark color, dried appearance)",
    "two_step_validation": "STEP A VALIDATED: Dark color → processed category code selected. STEP B VALIDATED: No label qualifiers → Other suffix applied."
  }}
}}

**IF PRODUCT NOT IN DOCUMENT:**
{{
  "classifications": [],
  "visual_analysis": {{...}},
  "not_in_document": true,
  "reason": "explain what the product is and why it's not in the HS document"
}}

**CRITICAL OUTPUT REQUIREMENTS:**

1. **Structure:** Start with label_text_extraction, then classifications, then visual_analysis
2. **Text Extraction First:** Complete Phase 1 extraction before any classification
3. **Validation:** Every classification MUST reference what was found (or not found) on the label in natural language
4. **Qualifier Codes:** To use ANY code with qualifiers (organic, decaf, variety):
   - The qualifier MUST appear in the extracted text or as a visible certification
   - If NOT found → use general/"Other" code
   - Reasoning MUST explain in plain language: "No organic certification text visible, therefore using the general classification"
5. **No Assumptions:** Decorative imagery (leaves, flowers, natural scenes) is NOT proof of certification
6. **Confidence:** Be HARSH with scores - Phase 1 confirmation required for high confidence on specific codes
7. **Format:** 
   - Your response MUST START with {{ and END with }}
   - Do NOT add markdown formatting (no ```, no ```json, no **bold**)
   - Do NOT add text labels (no "Answer:", no "JSON Output:", no "Here is the JSON:")
   - Do NOT add explanatory text before or after the JSON
   - Output ONLY the raw JSON object - nothing else

**REMEMBER:** 
- Phase 1 FIRST: Extract text → Then Phase 2: Classify
- No qualifiers or certifications found → use "Other" suffix codes
- CRITICAL: In the "reasoning" field, write ONLY natural English - NEVER use technical terms like 'Phase 1', 'visible_text', 'certification_marks', 'qualifier_keywords', or '[]'
- Write as if explaining to a customs officer who doesn't know JSON or programming
- Example good reasoning: "The packaging shows brand names but no organic certifications. Therefore, the general code is used."
- Example BAD reasoning: "Phase 1 extraction shows visible_text: [] and certification_marks: []" ← DO NOT DO THIS

Begin your response with {{ now:
{{"""

            # Prepare the API request headers
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }

            # Watsonx API payload
            payload = {
                "model_id": "meta-llama/llama-3-2-90b-vision-instruct",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}"
                                },
                            },
                        ],
                    }
                ],
                "parameters": {
                    "decoding_method": "greedy",
                    "max_new_tokens": 3000,
                    "temperature": 0.0,
                    "min_new_tokens": 100,
                },
                "project_id": self.project_id,
            }

            # Make the API call
            api_url = f"{self.url}/ml/v1/text/chat?version=2023-05-29"

            retry_info = f" (Retry {retry_count + 1}/{max_retries + 1})" if retry_count > 0 else ""
            print(f"Making HS Code classification API call{retry_info}...")

            response = requests.post(api_url, headers=headers, json=payload, timeout=60)

            # If 401, refresh token and retry once
            if response.status_code == 401:
                print("Token expired, refreshing...")
                access_token = self.get_access_token(force_refresh=True)
                headers["Authorization"] = f"Bearer {access_token}"
                response = requests.post(
                    api_url, headers=headers, json=payload, timeout=60
                )

            if response.status_code == 200:
                result = response.json()

                # Extract generated text from response
                if "choices" in result:
                    generated_text = result["choices"][0]["message"]["content"]
                else:
                    generated_text = result.get("results", [{}])[0].get(
                        "generated_text", ""
                    )

                print(f"HS Code classification response received (length: {len(generated_text)})")
                
                # Log first 200 chars of response for debugging
                preview = generated_text[:200] if len(generated_text) > 200 else generated_text
                print(f"Response preview: {repr(preview)}")

                # Try to parse JSON from the response (robust parsing like overgoods)
                try:
                    json_str = generated_text.strip()
                    print(f"After .strip(): length={len(json_str)}, last char='{json_str[-1] if json_str else 'EMPTY'}' (ASCII {ord(json_str[-1]) if json_str else 0})")

                    # Handle markdown code blocks: ```json\n{...}\n``` or ```\n{...}\n```
                    if "```" in json_str:
                        code_block_match = re.search(
                            r"```(?:json)?\s*\n?(.*?)\n?```", json_str, re.DOTALL
                        )
                        if code_block_match:
                            json_str = code_block_match.group(1).strip()
                            print(f"Extracted JSON from markdown code block")

                    # If it starts with text before JSON, extract just the JSON part
                    if not json_str.startswith("{"):
                        start_idx = json_str.find("{")
                        if start_idx != -1:
                            print(f"  Trimming start - found '{{' at position {start_idx}")
                            json_str = json_str[start_idx:]
                        else:
                            # NO JSON FOUND AT ALL - Model completely ignored instructions
                            print(f"  ❌ CRITICAL: No JSON found in response! Model returned non-JSON content.")
                            print(f"  Full response: {repr(generated_text)}")
                            
                            # Retry if we haven't exceeded max retries
                            if retry_count < max_retries:
                                print(f"  🔄 RETRY ATTEMPT {retry_count + 1}/{max_retries}: Calling API again...")
                                return self.classify_hs_code(image_path, retry_count=retry_count + 1, max_retries=max_retries)
                            
                            # Max retries exceeded
                            return {
                                "success": False,
                                "error": f"AI model returned non-JSON response after {max_retries + 1} attempts. The model may be experiencing issues. Please try again later or with a different image.",
                                "raw_response": generated_text,
                                "error_type": "no_json_in_response"
                            }

                    # If it has text after JSON, extract just the JSON part
                    original_len = len(json_str)
                    if not json_str.endswith("}"):
                        last_char = json_str[-1] if json_str else ''
                        print(f"  ⚠️  JSON doesn't end with '}}' - last char: '{last_char}' (ASCII: {ord(last_char) if last_char else 0})")
                        print(f"  Last 40 chars: ...{repr(json_str[-40:])}")

                        # Find the matching closing brace by counting nesting levels
                        brace_count = 0
                        end_idx = -1
                        for i, char in enumerate(json_str):
                            if char == "{":
                                brace_count += 1
                            elif char == "}":
                                brace_count -= 1
                                if brace_count == 0:
                                    end_idx = i + 1
                                    break

                        if end_idx > 0:
                            print(f"  ✓ Found MATCHING '}}' at position: {end_idx - 1} (will cut to length {end_idx})")
                            json_str = json_str[:end_idx]
                            chars_cut = original_len - len(json_str)
                            print(f"  ✂️  CUT OFF {chars_cut} chars! ({original_len} → {len(json_str)})")
                            print(f"  After trim, last 40 chars: ...{repr(json_str[-40:])}")
                        else:
                            # FALLBACK: The { trick causes AI to omit the final }
                            # If we have opening brace but no closing, just add it!
                            print(f"  ⚠️  Could not find matching closing brace")
                            print(f"  🔧 FALLBACK: Attempting to complete JSON by adding missing '}}' ")

                            # Count how many braces are unmatched
                            open_count = json_str.count("{")
                            close_count = json_str.count("}")
                            missing_braces = open_count - close_count

                            if missing_braces > 0:
                                print(f"  Missing {missing_braces} closing brace(s), adding them...")
                                json_str = json_str + ("}" * missing_braces)
                                print(f"  ✓ Completed JSON! New last 40 chars: ...{repr(json_str[-40:])}")
                            else:
                                print(f"  ❌ Brace count mismatch - cannot auto-fix")

                    # CRITICAL: Unescape JSON BEFORE checking if it's valid
                    if "\\{" in json_str or "\\}" in json_str or "\\[" in json_str or "\\]" in json_str:
                        print("Detected escaped JSON, unescaping...")
                        json_str = json_str.replace("\\{", "{").replace("\\}", "}")
                        json_str = json_str.replace("\\[", "[").replace("\\]", "]")
                        json_str = json_str.replace('\\"', '"')

                    # Remove inline comments (// ...) that AI sometimes adds
                    if "//" in json_str:
                        print("Removing inline comments from JSON...")
                        # Remove comments but preserve the line structure
                        lines = json_str.split('\n')
                        cleaned_lines = []
                        for line in lines:
                            # Find // outside of strings
                            if '//' in line:
                                # Simple approach: remove everything after // if not in a string value
                                # Check if // appears after a quote closure
                                comment_idx = line.find('//')
                                before_comment = line[:comment_idx]
                                # Count quotes before comment to see if we're in a string
                                quote_count = before_comment.count('"') - before_comment.count('\\"')
                                if quote_count % 2 == 0:  # Even number of quotes = not in string
                                    line = before_comment.rstrip() 
                            cleaned_lines.append(line)
                        json_str = '\n'.join(cleaned_lines)
                        print(f"After comment removal, length: {len(json_str)}")
                    
                    # Remove trailing commas before closing braces/brackets (common AI mistake)
                    json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)

                    if json_str.startswith("{") and json_str.endswith("}"):
                        parsed_result = json.loads(json_str)
                        print(f"✓ Successfully parsed JSON response")
                        
                        # POST-PROCESS: Apply Python-level HS code matching
                        parsed_result = self._apply_smart_hs_matching(parsed_result)

                        return {
                            "success": True,
                            "data": parsed_result,
                            "raw_response": generated_text,
                        }
                    else:
                        print(f"❌ JSON validation failed - doesn't start/end with braces")
                        return {
                            "success": False,
                            "error": "Could not find valid JSON in response",
                            "raw_response": generated_text,
                        }

                except json.JSONDecodeError as e:
                    print(f"❌ JSON parsing error: {e}")
                    return {
                        "success": False,
                        "error": f"JSON parsing error: {str(e)}",
                        "raw_response": generated_text,
                    }
            else:
                error_msg = f"API call failed: {response.status_code} - {response.text}"
                print(error_msg)
                return {"success": False, "error": error_msg}

        except Exception as e:
            error_msg = f"Error classifying HS code: {str(e)}"
            print(error_msg)
            return {"success": False, "error": error_msg}
