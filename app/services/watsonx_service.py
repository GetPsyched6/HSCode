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

═══════════════════════════════════════════════════════════════════════
PHASE 1: LABEL TEXT EXTRACTION (Complete this FIRST - MANDATORY)
═══════════════════════════════════════════════════════════════════════

Before making ANY classification decisions, you must extract information from the label:

1. **Read ALL visible text** on the product label/packaging (brand names, product names, descriptions, weight, etc.)
2. **Identify certification seals/logos** - Look for actual certification marks (USDA Organic seal, Fair Trade logo, certification body logos)
3. **List regulatory marks** - Any certification numbers, approval codes, or regulatory stamps
4. **Extract qualifier keywords** - Words that indicate specific product attributes: ORGANIC, CERTIFIED, DECAF, DECAFFEINATED, ARABICA, ROBUSTA, FLAVORED, etc.

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
- Packaging with floral design but no certification text → certification_marks: [], qualifier_keywords: []
- Packaging with "USDA Organic" seal visible → certification_marks: ["USDA Organic seal"], qualifier_keywords: ["ORGANIC"]
- Packaging with "100% Arabica" text → qualifier_keywords: ["ARABICA", "100% ARABICA"]

═══════════════════════════════════════════════════════════════════════
PHASE 2: HS CODE SELECTION (Use ONLY Phase 1 results)
═══════════════════════════════════════════════════════════════════════

Now classify using ONLY the text/marks you extracted in Phase 1.

**CRITICAL ANALYSIS REQUIREMENTS:**

1. **VISUAL INSPECTION** - Look carefully at EVERY detail:
   - Color, shade, and tone of the product
   - Physical state (whole, ground, powder, leaves, liquid, solid)
   - Processing indicators (roasting, fermentation, drying, cooking, etc.)
   - Packaging (retail containers, bulk, bags, boxes, labels)
   - Size, shape, texture, and physical characteristics

2. **PRODUCT IDENTIFICATION** - Determine:
   - Base product category (what is it fundamentally?)
   - Processing or preparation state (raw, processed, cooked, fermented, etc.)
   - Variety, species, or type (ONLY if confirmed in Phase 1 extraction)
   - Special attributes (ONLY if confirmed in Phase 1 extraction)
   - Packaging type, size, and retail/bulk format

3. **HS CODE MATCHING** - Match against the document:
   - Find ALL codes that could reasonably apply
   - Rank by confidence based on visual evidence
   - Consider edge cases and borderline classifications
   - Pay close attention to processing distinctions in the HS document
   - Match specific characteristics (organic, flavored, packaging size, etc.)

   **EVIDENCE-BASED CLASSIFICATION HIERARCHY:**
   When multiple codes differ by a SPECIFIC QUALIFIER (e.g., "certified organic" vs "other", "decaffeinated" vs "not decaffeinated", specific variety vs general):
   
   a) IDENTIFY THE DISTINGUISHER: What attribute makes one code different from another?
      - Certification status (organic, fair trade, etc.)
      - Processing method (decaffeinated, fermented, roasted, etc.)
      - Material/variety type (Arabica vs Robusta, cotton vs polyester, etc.)
      - Special characteristics (flavored, grade, quality designation, etc.)
   
   b) REQUIRE VISUAL EVIDENCE (verified in Phase 1):
      - Only use SPECIFIC codes if you can SEE proof of the distinguishing attribute
      - Acceptable evidence:
        * Explicit text stating the attribute ("CERTIFIED ORGANIC", "DECAFFEINATED", "100% COTTON")
        * Official certification seals/logos (USDA Organic seal, Fair Trade logo, etc.)
        * Regulatory marks or certification numbers
        * Unambiguous physical differences that ONLY occur in the specific variant
      - NOT acceptable evidence:
        * Decorative elements (flowers, leaves, natural imagery) ≠ certification
        * Color schemes (green packaging ≠ organic)
        * Artistic design choices or marketing aesthetics
        * Assumptions like "looks premium so probably certified"
        * Inferences like "has natural imagery so must be organic"
        * "Possibly", "likely", "suggests", "indicates" reasoning
   
   c) MANDATORY VALIDATION RULE - Cross-check with Phase 1:
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
      "Examples: 'ORGANIC', 'CERTIFIED', 'DECAF', 'ARABICA', 'ROBUSTA', 'FLAVORED'",
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
      "reasoning": "detailed explanation that MUST reference label_text_extraction. State: (1) What text/marks found in Phase 1, (2) Which qualifiers are present/absent in label_text_extraction, (3) Why you selected this specific code suffix based on extracted text. Example: 'Based on label_text_extraction, found visible_text: [Bonhomia, Nirvana, Premium...] but certification_marks: [] and qualifier_keywords: []. Since NO ORGANIC text or certification found in Phase 1, using suffix 20 (Other) instead of 15 (Certified organic).'",
      "confidence_score": 0.0 to 1.0,
      "key_characteristics": [
        "list of observed characteristics that support this classification"
      ]
    }}
  ],
  "visual_analysis": {{
    "product_type": "primary product category",
    "color": "exact color/shade observed",
    "processing_state": "processing or preparation state",
    "packaging": "packaging description if visible",
    "decorative_elements": "describe any decorative imagery (flowers, leaves, patterns) - separate from certifications",
    "label_text_summary": "brief summary referencing what was found/not found in label_text_extraction"
  }},
  "not_in_document": false
}}

**EXAMPLE - Nirvana Coffee with floral design but NO certification:**
{{
  "label_text_extraction": {{
    "visible_text": ["Bonhomia", "Gourmet Coffees & Teas", "NIRVANA", "Premium", "Speciality Coffee Blend", "Medium-Dark", "200g"],
    "certification_marks": [],  // No USDA Organic or other certification seals visible
    "regulatory_marks": [],
    "qualifier_keywords": []  // No ORGANIC, DECAF, or ARABICA text visible
  }},
  "classifications": [
    {{
      "hs_code": "0901.21.00",
      "stat_suffix": "20",  // Using "Other" because no certification in Phase 1
      "article_description": "Coffee, roasted: Not decaffeinated: In retail containers weighing 2 kg or less: Arabica: Other",
      "reasoning": "Phase 1 extraction shows visible_text includes product names but certification_marks: [] and qualifier_keywords: []. Despite decorative floral imagery on packaging, NO 'CERTIFIED ORGANIC' text or USDA seal found. NO 'ARABICA' text found on label. Therefore using suffix 20 (Other) instead of 15 (Certified organic). Roasted state confirmed by brown beans visible.",
      "confidence_score": 0.85
    }}
  ]
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
3. **Validation:** Every classification MUST cross-reference label_text_extraction in the reasoning
4. **Qualifier Codes:** To use ANY code with qualifiers (organic, decaf, variety):
   - The qualifier MUST appear in label_text_extraction.qualifier_keywords OR certification_marks
   - If NOT in extraction → use general/"Other" code
   - Reasoning MUST explain: "qualifier_keywords: [] so using suffix 20 not 15"
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
- Empty qualifier_keywords and certification_marks → use "Other" suffix codes
- Reasoning must reference what was/wasn't found in label_text_extraction

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
                    "max_new_tokens": 1500,
                    "temperature": 0.0,
                    "top_p": 0.9,
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
