import os
from dotenv import load_dotenv

load_dotenv()

# Watsonx Configuration
WATSONX_API_KEY = os.getenv("WATSONX_API_KEY", "your_api_key_here")
WATSONX_PROJECT_ID = os.getenv("WATSONX_PROJECT_ID", "your_project_id_here")
WATSONX_URL = os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")

# Application Configuration
UPLOAD_DIR = "uploads"
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

# HS Code Document Snippet
HS_CODE_DOCUMENT = """HTS_Code,Description,Unit_of_Quantity,Rate_General,Rate_Special,Rate_Column_2
0901.11.00.15,"Coffee, not roasted: Not decaffeinated: Arabica: Certified organic",kg,"Free 1/","",Free
0901.11.00.25,"Coffee, not roasted: Not decaffeinated: Arabica: Other",kg,"Free 1/","",Free
0901.11.00.35,"Coffee, not roasted: Not decaffeinated: Robusta: Certified organic",kg,"Free 1/","",Free
0901.11.00.40,"Coffee, not roasted: Not decaffeinated: Robusta: Other",kg,"Free 1/","",Free
0901.11.00.50,"Coffee, not roasted: Not decaffeinated: Other: Certified organic",kg,"Free 1/","",Free
0901.11.00.65,"Coffee, not roasted: Not decaffeinated: Other: Other",kg,"Free 1/","",Free
0901.12.00.20,"Coffee, not roasted: Decaffeinated: Arabica: Certified organic",kg,"Free 1/","",Free
0901.12.00.35,"Coffee, not roasted: Decaffeinated: Arabica: Other",kg,"Free 1/","",Free
0901.12.00.40,"Coffee, not roasted: Decaffeinated: Robusta: Certified organic",kg,"Free 1/","",Free
0901.12.00.55,"Coffee, not roasted: Decaffeinated: Robusta: Other",kg,"Free 1/","",Free
0901.12.00.60,"Coffee, not roasted: Decaffeinated: Other: Certified organic",kg,"Free 1/","",Free
0901.12.00.75,"Coffee, not roasted: Decaffeinated: Other: Other",kg,"Free 1/","",Free
0901.21.00.15,"Coffee, roasted: Not decaffeinated: In retail containers weighing 2 kg or less: Arabica: Certified organic",kg,"Free 1/","",Free
0901.21.00.20,"Coffee, roasted: Not decaffeinated: In retail containers weighing 2 kg or less: Arabica: Other",kg,"Free 1/","",Free
0901.21.00.25,"Coffee, roasted: Not decaffeinated: In retail containers weighing 2 kg or less: Robusta: Certified organic",kg,"Free 1/","",Free
0901.21.00.29,"Coffee, roasted: Not decaffeinated: In retail containers weighing 2 kg or less: Robusta: Other",kg,"Free 1/","",Free
0901.21.00.40,"Coffee, roasted: Not decaffeinated: In retail containers weighing 2 kg or less: Other: Certified organic",kg,"Free 1/","",Free
0901.21.00.49,"Coffee, roasted: Not decaffeinated: In retail containers weighing 2 kg or less: Other: Other",kg,"Free 1/","",Free
0901.22.00.35,"Coffee, roasted: Decaffeinated: In retail containers weighing 2 kg or less: Arabica: Certified organic",kg,"Free 1/","",Free
0901.22.00.40,"Coffee, roasted: Decaffeinated: In retail containers weighing 2 kg or less: Arabica: Other",kg,"Free 1/","",Free
0901.22.00.50,"Coffee, roasted: Decaffeinated: In retail containers weighing 2 kg or less: Robusta: Certified organic",kg,"Free 1/","",Free
0901.22.00.55,"Coffee, roasted: Decaffeinated: In retail containers weighing 2 kg or less: Robusta: Other",kg,"Free 1/","",Free
0901.22.00.65,"Coffee, roasted: Decaffeinated: In retail containers weighing 2 kg or less: Other: Certified organic",kg,"Free 1/","",Free
0901.22.00.70,"Coffee, roasted: Decaffeinated: In retail containers weighing 2 kg or less: Other: Other",kg,"Free 1/","",Free
0901.90.10.00,"Coffee husks and skins.",kg,"Free 1/","","10%"
0901.90.20.00,"Coffee substitutes containing coffee.",kg,"1.5¢/kg","Free (A+, AU, BH, CL, CO, D, E, IL, JO, KR, MA, OM, P, PA, PE, S, SG)","6.6¢/kg"
0902.10.10.15,"Tea, whether or not flavored: Green tea (not fermented) in immediate packings of a content not exceeding 3 kg: Flavored: Certified organic",kg,"6.4% 1/","Free (A, AU, BH, CL, CO, D, E, IL, JO, KR, MA, OM, P, PA, PE, S, SG) 3.2% (JP)","20%"
0902.10.10.50,"Tea, whether or not flavored: Green tea (not fermented) in immediate packings of a content not exceeding 3 kg: Flavored: Other",kg,"6.4% 1/","Free (A, AU, BH, CL, CO, D, E, IL, JO, KR, MA, OM, P, PA, PE, S, SG) 3.2% (JP)","20%"
0902.10.90.15,"Tea, whether or not flavored: Green tea (not fermented) in immediate packings of a content not exceeding 3 kg: Other: Certified organic",kg,"Free 1/","",Free
0902.10.90.50,"Tea, whether or not flavored: Green tea (not fermented) in immediate packings of a content not exceeding 3 kg: Other: Other",kg,"Free 1/","",Free
0902.20.10.00,"Tea, whether or not flavored: Other green tea (not fermented): Flavored",kg,"6.4% 1/","Free (A*, AU, BH, CL, CO, D, E, IL, JO, KR, MA, OM, P, PA, PE, S, SG) 3.2% (JP)","20%"
0902.20.90.15,"Tea, whether or not flavored: Other green tea (not fermented): Other: Certified organic",kg,"Free 1/","",Free
0902.20.90.50,"Tea, whether or not flavored: Other green tea (not fermented): Other: Other",kg,"Free 1/","",Free
0902.30.00.15,"Tea, whether or not flavored: Black tea (fermented) and partly fermented tea, in immediate packings of a content not exceeding 3 kg: In tea bags: Certified organic",kg,"Free 1/","",Free
0902.30.00.50,"Tea, whether or not flavored: Black tea (fermented) and partly fermented tea, in immediate packings of a content not exceeding 3 kg: In tea bags: Other",kg,"Free 1/","",Free
0902.30.00.90,"Tea, whether or not flavored: Black tea (fermented) and partly fermented tea, in immediate packings of a content not exceeding 3 kg: Other",kg,"Free 1/","",Free
0902.40.00.00,"Tea, whether or not flavored: Other black tea (fermented) and other partly fermented tea...",kg,"Free 1/","",Free
0903.00.00.00,"Maté...",kg,"Free 1/","","10%"""
