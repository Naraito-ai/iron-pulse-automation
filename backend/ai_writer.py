"""
ai_writer.py — Viral Fitness Content Engine.
Generates 6 proven Instagram growth content types for  fitness page.
"""

import json
import logging
import random
from config import AI_PROVIDER, GEMINI_API_KEY, OPENAI_API_KEY, DEMO_MODE, BRAND_NAME

logger = logging.getLogger(__name__)


def get_gemini_client():
    """Return a configured Gemini GenerativeModel for comment replies, or None if not available."""
    if not GEMINI_API_KEY:
        logger.warning("No GEMINI_API_KEY — auto-commenting disabled")
        return None
    try:
        from google import genai
        client = genai.Client(api_key=GEMINI_API_KEY)
        return client
    except Exception as e:
        logger.error("Failed to init Gemini client: %s", e)
        return None


# ─── Content Types ────────────────────────────────────────────────────────────

CONTENT_TYPES = [
    "hot_take",       # Controversial opinion → debate → reach
    "quick_tip",      # Fast punchy tip → high completion rate
    "save_list",      # "5 mistakes killing your gains" → saves
    "myth_buster",    # Myth vs Fact → saves + shares
    "meme_relatable", # Relatable gym humor → shares
    "transformation", # Before/after tips → emotional → saves
]


# ─── System Prompt ────────────────────────────────────────────────────────────

SYSTEM_PROMPT = f"""You are the viral content strategist for {BRAND_NAME}, 
a fitness Instagram page that's growing FAST. You write content that:

- STOPS the scroll in 0.5 seconds (powerful hook)
- Makes people SAVE (list content, tips, myth busters)
- Makes people COMMENT (controversial opinions, questions)
- Makes people SHARE (relatable, funny, shocking)
- Is SCIENCE-BASED but written in plain English
- NEVER sounds like a product ad or generic fitness advice
- Uses GYM CULTURE language: gains, natty, bro split, pump, grind

Your content types and their goals:
1. HOT TAKE: Controversial fitness opinion → debate → comments
2. QUICK TIP: One powerful tip → high completion rate on Reels
3. SAVE LIST: "5 mistakes..." or "3 things..." → saves
4. MYTH BUSTER: Expose a common gym myth → saves + shares  
5. MEME RELATABLE: Funny gym situation → shares
6. TRANSFORMATION TIPS: Before/after style advice → emotional saves"""


# ─── Prompt Templates by Content Type ────────────────────────────────────────

PROMPTS = {

"hot_take": """Generate a VIRAL HOT TAKE / controversial opinion post for fitness Instagram.
Topic context: {title}

Rules:
- Headline MUST be aggressively polarizing and stop the scroll (e.g. "Unpopular Opinion: Cardio is useless", "Creatine is making you fat").
- Bullet points = the argument FOR the hot take (science-backed but written like a cheat code).
- Caption starts with the hot take as a BOLD statement, ends with a strong debate question.
- MUST include an SEO-rich paragraph at the very bottom of the caption (hidden below hashtags) to boost algorithmic reach (e.g., "SEO: fitness tips, gym advice, bodybuilding, workout hacks, losing weight").
- CTA should spark angry/passionate comments.

Return JSON:
{{
  "content_type": "hot_take",
  "headline": "Aggressively polarizing hook in ≤7 words",
  "subheadline": "The provocative follow-up in 10-12 words",
  "bullet_points": [
    "Argument point 1 with specific fact",
    "Argument point 2 with specific fact",
    "Argument point 3 with specific fact"
  ],
  "stat_highlight": "One shocking stat that supports the hot take",
  "caption": "Instagram caption 150-250 chars. Open bold. End with debate question. Use 2-3 line breaks. Then add hashtags. Then add 'SEO: [comma separated list of 15 long-tail fitness keywords]'",
  "hashtags": "#HotTake #FitnessMyths #GymTruth #FitnessFacts #GymLife #Bodybuilding #Fitness #WorkoutTips #GymMotivation #",
  "cta": "Comment 'LINK' for my full guide, or debate me below 👇"
}}""",

"quick_tip": """Generate a VIRAL CHEAT CODE / QUICK TIP post for a fitness Instagram Reel (fast paced).
Topic context: {title}

Rules:
- ONE single powerful actionable "Hack" or "Cheat Code".
- Headline = "Fitness Cheat Code #X" or a highly shocking actionable tip.
- Body = why it works (1 sentence).
- Caption is SHORT and includes an SEO rich paragraph at the bottom.
- CTA = "Comment 'GUIDE' for my full protocol".

Return JSON:
{{
  "content_type": "quick_tip",
  "headline": "The single cheat code tip in ≤7 words (e.g. 'Fitness Cheat Code: 3 Min Rest')",
  "subheadline": "Why this works in 8-10 words",
  "bullet_points": [
    "The science behind it in simple English",
    "Who benefits most from this hack",
    "How to actually apply it today"
  ],
  "stat_highlight": "A number that proves it works (e.g. '2x more strength gains')",
  "caption": "Short punchy caption under 100 chars. Then add hashtags. Then add 'SEO: [15 long-tail fitness keywords]'",
  "hashtags": "#GymTip #WorkoutTips #FitnessHack #GainsTip #GymLife #Fitness #Bodybuilding #GymMotivation #TrainingTips #",
  "cta": "Comment 'GUIDE' for my full protocol 💪"
}}""",

"save_list": """Generate a VIRAL SAVE-WORTHY LIST post for fitness Instagram.
Topic context: {title}

Rules:
- Title follows "X Secret Rules that [outcome]" or "X Things Your Trainer Won't Tell You" format.
- MUST include "Save this 🔖" in the caption.
- Each bullet = one item from the list (punchy, highly specific, slightly controversial if possible).
- Caption must include an SEO-rich paragraph at the very bottom (hidden below hashtags) to boost algorithmic reach.

Return JSON:
{{
  "content_type": "save_list",
  "headline": "List title in ≤7 words (e.g. '3 Secrets Your Trainer Is Hiding')",
  "subheadline": "What they'll learn from saving this",
  "bullet_points": [
    "Rule #1 — what it is and the quick fix",
    "Rule #2 — what it is and the quick fix",
    "Rule #3 — what it is and the quick fix"
  ],
  "stat_highlight": "A stat that shows how rare this knowledge is",
  "caption": "Caption 200-280 chars. Open with hook. Mention 'Save 🔖'. Use 2-3 line breaks. Then add hashtags. Then add 'SEO: [comma separated list of 15 long-tail fitness keywords]'",
  "hashtags": "#GainsTips #GymMistakes #FitnessAdvice #WorkoutTips #GymLife #Bodybuilding #Fitness #GymMotivation #FitnessTips #",
  "cta": "Save 🔖 + Comment 'WORKOUT' for my free program"
}}""",

"myth_buster": """Generate a VIRAL MYTH BUSTER post for fitness Instagram.
Topic context: {title}

Rules:
- Expose a VERY common fitness myth that even experienced gym-goers believe.
- Headline MUST be controversial ("The Biggest Lie You've Been Told About X").
- Bullet points = the brutal facts that BUST the myth.
- Caption starts with "We've all been lied to..." then drops the truth.
- Caption must include an SEO-rich paragraph at the very bottom (hidden below hashtags) to boost algorithmic reach.

Return JSON:
{{
  "content_type": "myth_buster",
  "headline": "The shocking myth-busting hook in ≤7 words",
  "subheadline": "The brutal truth reveal in 4-6 words",
  "bullet_points": [
    "The actual science/truth about this myth",
    "Why the fitness industry lied to you",
    "What you should actually do instead"
  ],
  "stat_highlight": "A research stat that proves the myth wrong",
  "caption": "Caption 200-280 chars. Start with 'We've all been lied to...'. Drop the truth. Use 2-3 line breaks. Then add hashtags. Then add 'SEO: [15 long-tail fitness keywords]'",
  "hashtags": "#FitnessMyths #GymFacts #FitnessTruth #ScienceOfFitness #GymLife #Bodybuilding #WorkoutFacts #GymMotivation #FitnessEducation #",
  "cta": "Share to save a bro from this lie 🔁"
}}""",

"meme_relatable": """Generate a VIRAL RELATABLE GYM MEME / humor post for fitness Instagram.
Topic context: {title}

Rules:
- Must be HYPER-RELATABLE to modern gym culture (e.g. gym crushes, missing PRs, taking pre-workout dry, waiting for squat racks).
- "POV:", "Nobody:", "Me:", "Every gym bro:" format works great.
- Bullet points = the punchlines / relatable scenarios.
- Caption is short, funny, and MUST include an SEO-rich paragraph at the very bottom (hidden below hashtags) to boost algorithmic reach.

Return JSON:
{{
  "content_type": "meme_relatable",
  "headline": "The meme setup in 4-6 words",
  "subheadline": "The punchline or relatable follow-up in 4-6 words",
  "bullet_points": [
    "Relatable gym scenario 1 (funny, specific)",
    "Relatable gym scenario 2 (funny, specific)",
    "Relatable gym scenario 3 (funny, specific)"
  ],
  "stat_highlight": "Funny fake stat or relatable number (e.g. '99% of guys skip calves')",
  "caption": "Funny caption 100-180 chars. Use gym humor. End with 'Tag your gym partner 😂'. Use 2-3 line breaks. Then add hashtags. Then add 'SEO: [15 long-tail fitness keywords]'",
  "hashtags": "#GymMemes #GymHumor #GymLife #GymProblems #GymBro #FitnessMemes #GymFunny #WorkoutMemes #GymMotivation #",
  "cta": "Tag your gym partner who does this 😂"
}}""",

"transformation": """Generate a VIRAL TRANSFORMATION TIPS post for fitness Instagram.
Topic context: {title}

Rules:  
- Frame as brutal truths or "cheat codes" for transformation.
- Bullet points = the specific habits/changes that actually drive transformation.
- Very emotional, aspiration-driven, but straightforward.
- Caption MUST include an SEO-rich paragraph at the very bottom (hidden below hashtags) to boost algorithmic reach.

Return JSON:
{{
  "content_type": "transformation",
  "headline": "Transformation angle in 4-6 words",
  "subheadline": "The aspiration promise in 4-6 words",
  "bullet_points": [
    "Brutal truth/habit #1 — specific and actionable",
    "Brutal truth/habit #2 — specific and actionable",
    "Brutal truth/habit #3 — specific and actionable"
  ],
  "stat_highlight": "A timeframe or result stat (e.g. '12 weeks to visible abs')",
  "caption": "Motivational caption 200-280 chars. Personal and inspiring. End with 'Save this 🔖'. Use 2-3 line breaks. Then add hashtags. Then add 'SEO: [15 long-tail fitness keywords]'",
  "hashtags": "#TransformationTips #FitnessJourney #GymTransformation #BodyTransformation #GymMotivation #FitnessGoals #GymLife #Bodybuilding #FitLife #",
  "cta": "Save this for when you need motivation 🔖"
}}""",

}


# ─── Demo Fallback Content ────────────────────────────────────────────────────

DEMO_CONTENT = {
    "hot_take": {
        "content_type": "hot_take",
        "headline": "Cardio Kills Muscle",
        "subheadline": "Stop running, start lifting",
        "bullet_points": [
            "Cardio eats muscle tissue",
            "Long runs lower testosterone",
            "Lift heavy weights instead"
        ],
        "stat_highlight": "30% less muscle growth",
        "caption": "Cardio is NOT the answer to body recomposition 🔥\n\nSave this before your next workout 👇",
        "hashtags": "#FitnessMyths #GymTruth #Bodybuilding #GymLife #Fitness #",
        "cta": "Agree or disagree? 👇"
    },
    "quick_tip": {
        "content_type": "quick_tip",
        "stat_highlight": "2x strength gains with 3 min rest vs 1 min",
        "caption": "Stop rushing your rest periods 🛑\n\nLonger rest = more reps next set = more gains 💪\n\nSave for your next workout 🔖",
        "hashtags": "#GymTip #WorkoutTips #FitnessHack #GainsTip #GymLife #Fitness #Bodybuilding #GymMotivation #TrainingTips #",
        "cta": "Save for your next workout 💪"
    },
    "save_list": {
        "content_type": "save_list",
        "headline": "5 Mistakes Killing Your Muscle Gains",
        "subheadline": "Stop doing these and watch your gains explode",
        "bullet_points": [
            "Not tracking protein — most gym-goers eat 40% less than needed",
            "Skipping progressive overload — same weight = same body forever",
            "Training to failure every set — destroys recovery and CNS"
        ],
        "stat_highlight": "80% of gym-goers never change their body after year 1",
        "caption": "Save 🔖 this before your next gym session.\n\nMost people train for YEARS with zero progress because of these mistakes.\n\nTag someone who needs to see this 👇",
        "hashtags": "#GainsTips #GymMistakes #FitnessAdvice #WorkoutTips #GymLife #Bodybuilding #Fitness #GymMotivation #FitnessTips #",
        "cta": "Save 🔖 + Tag someone who needs this"
    },
    "myth_buster": {
        "content_type": "myth_buster",
        "headline": "You Must Eat Protein Right After Workout",
        "subheadline": "The anabolic window is smaller than you think",
        "bullet_points": [
            "Research shows muscle protein synthesis stays elevated for 4-6 hours post-workout",
            "Total daily protein intake matters FAR more than timing",
            "Focus: hit 1.6-2.2g/kg protein across the whole day — timing is secondary"
        ],
        "stat_highlight": "4-6 hours of elevated protein synthesis after training",
        "caption": "MYTH: You must eat protein within 30 mins of training 🚫\n\nFACT: The window is 4-6 hours. Relax.\n\nShare this before your gym bro takes his shake mid-set 💀",
        "hashtags": "#FitnessMyths #GymFacts #FitnessTruth #ScienceOfFitness #GymLife #Bodybuilding #WorkoutFacts #GymMotivation #FitnessEducation #",
        "cta": "Share this before someone you know falls for this 🔁"
    },
    "meme_relatable": {
        "content_type": "meme_relatable",
        "headline": "POV: It Is Monday International Chest Day",
        "subheadline": "Every bench in the gym is taken at 6am somehow",
        "bullet_points": [
            "Me: does back. Everyone else: doing chest on back day too",
            "The guy who has been on the bench for 45 mins between sets",
            "Someone asking 'you using this?' about a bench I'm actively using"
        ],
        "stat_highlight": "100% of gym-goers have waited 20 mins for a bench on Monday",
        "caption": "Monday gym culture is something else 😂\n\nTag your gym partner who benches every single day 👇",
        "hashtags": "#GymMemes #GymHumor #GymLife #GymProblems #GymBro #FitnessMemes #GymFunny #WorkoutMemes #GymMotivation #",
        "cta": "Tag your gym partner who does this 😂"
    },
    "transformation": {
        "content_type": "transformation",
        "headline": "3 Habits That Changed My Body in 90 Days",
        "subheadline": "No crazy diet. No 2-hour workouts. Just these three things.",
        "bullet_points": [
            "Hit 1.8g protein per kg bodyweight every single day — non-negotiable",
            "Progressive overload on 3 core lifts: squat, bench, deadlift",
            "Sleep 7-9 hours — this is when the actual muscle is built"
        ],
        "stat_highlight": "90 days to a completely different body with consistency",
        "caption": "Nobody talks about how SIMPLE building muscle actually is 💪\n\nNo magic program. No expensive supplements.\n\nSave this for when you need motivation 🔖",
        "hashtags": "#TransformationTips #FitnessJourney #GymTransformation #BodyTransformation #GymMotivation #FitnessGoals #GymLife #Bodybuilding #FitLife #",
        "cta": "Save this for when you need motivation 🔖"
    },
}

# Order of content types per day (cycle through all 6)
CONTENT_TYPE_ORDER = [
    "hot_take",
    "quick_tip",
    "save_list",
    "myth_buster",
    "meme_relatable",
    "transformation",
]

# Which types to post as Reels vs Carousels
REEL_TYPES    = {"hot_take", "quick_tip", "meme_relatable"}
CAROUSEL_TYPES = {"save_list", "myth_buster", "transformation"}


# ─── LLM Providers ────────────────────────────────────────────────────────────

def _call_gemini(story: dict, content_type: str) -> dict:
    import os
    from google import genai
    from google.genai import types

    # Read key dynamically so Railway env vars are always picked up
    api_key = os.environ.get("GEMINI_API_KEY", GEMINI_API_KEY)
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")

    client = genai.Client(api_key=api_key)
    prompt = PROMPTS[content_type].format(
        title=story.get("title", ""),
        summary=story.get("summary", ""),
        source=story.get("source", ""),
    )

    for model_name in ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-2.0-flash-lite"]:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.9,
                ),
            )
            raw = response.text.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            return json.loads(raw)
        except Exception as e:
            logger.warning("Gemini model %s failed: %s", model_name, e)
            continue
    raise RuntimeError("All Gemini models failed")


def _call_openai(story: dict, content_type: str) -> dict:
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)
    prompt = PROMPTS[content_type].format(
        title=story.get("title", ""),
        summary=story.get("summary", ""),
        source=story.get("source", ""),
    )
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.9,
    )
    return json.loads(resp.choices[0].message.content)


# ─── Main Writer ──────────────────────────────────────────────────────────────

def generate_content_for_story(story: dict, rank: int = 0) -> dict:
    """Generate viral content for a single story, using the right content type for that slot."""
    import os
    content_type = CONTENT_TYPE_ORDER[rank % len(CONTENT_TYPE_ORDER)]

    if DEMO_MODE:
        logger.info("[DEMO] Generating %s content for slot %d", content_type, rank + 1)
        content = DEMO_CONTENT[content_type].copy()
        content["post_format"] = "reel" if content_type in REEL_TYPES else "carousel"
        return content

    # Read key dynamically — critical for Railway where env vars load after module import
    live_gemini_key = os.environ.get("GEMINI_API_KEY", GEMINI_API_KEY)
    live_openai_key = os.environ.get("OPENAI_API_KEY", OPENAI_API_KEY)
    live_provider   = os.environ.get("AI_PROVIDER", AI_PROVIDER)

    logger.info("Generating %s content for: %s", content_type, story.get("title", "")[:50])
    try:
        if live_provider == "openai" and live_openai_key:
            content = _call_openai(story, content_type)
        elif live_gemini_key:
            content = _call_gemini(story, content_type)
        else:
            logger.warning("No AI provider configured, using demo content")
            content = DEMO_CONTENT[content_type].copy()

        # Validate fields
        required = ["headline", "bullet_points", "caption", "hashtags", "cta"]
        for field in required:
            if field not in content:
                raise ValueError(f"Missing field: {field}")

        if isinstance(content["bullet_points"], str):
            content["bullet_points"] = [content["bullet_points"]]

        content.setdefault("content_type", content_type)
        content.setdefault("stat_highlight", "")
        content.setdefault("subheadline", "")
        content["post_format"] = "reel" if content_type in REEL_TYPES else "carousel"
        logger.info("AI content (%s) generated successfully", content_type)
        return content

    except Exception as e:
        logger.error("AI content generation failed: %s — falling back to demo", e)
        content = DEMO_CONTENT[content_type].copy()
        content["post_format"] = "reel" if content_type in REEL_TYPES else "carousel"
        return content


def generate_all_content(stories: list[dict]) -> list[dict]:
    """Generate viral content for all stories."""
    results = []
    for i, story in enumerate(stories):
        content = generate_content_for_story(story, rank=i)
        content["rank"]  = i + 1
        content["story"] = story
        results.append(content)
        logger.info("Content ready for story %d/%d [%s]",
                    i + 1, len(stories), content.get("content_type", "?"))
    return results
