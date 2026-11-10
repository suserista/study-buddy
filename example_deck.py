"""Ready-made demo study set for the "Try the example" button.

This deck is inserted WITHOUT calling Gemini — every text below is pre-written,
in exactly the same shape the AI is asked to return (see PROMPT_TEMPLATE in
app.py), so it goes through the same saving and rendering code as a real,
generated study set. That makes the app demo-able with zero API usage.
"""

EXAMPLE_TITLE = "Photosynthesis — The Basics"

EXAMPLE_NOTES = """Photosynthesis — lecture notes

Photosynthesis is the process plants, algae and some bacteria use to turn
light energy into chemical energy. They take in carbon dioxide from the air
and water from the soil, and use light to build glucose (a sugar) and release
oxygen as a by-product.

Word equation: 6 CO2 + 6 H2O + light energy -> C6H12O6 + 6 O2

Where it happens: inside chloroplasts, mainly in the mesophyll cells of
leaves. Chloroplasts contain chlorophyll, a green pigment that absorbs red
and blue light and reflects green light (that is why leaves look green).
Gases enter and leave the leaf through tiny pores called stomata.

Two stages:
1. Light-dependent reactions — happen in the thylakoid membranes. Light splits
   water molecules (photolysis), releasing oxygen. The energy is stored in ATP
   and NADPH.
2. Light-independent reactions (the Calvin cycle) — happen in the stroma, the
   fluid around the thylakoids. ATP and NADPH are used to fix carbon dioxide
   into glucose. This stage does not use light directly.

Limiting factors: the rate of photosynthesis is limited by light intensity,
carbon dioxide concentration and temperature. In low light the process slows
down; too little CO2 slows it down; enzymes work best at moderate
temperatures.

Why it matters: photosynthesis is the base of almost every food chain, and it
produces practically all the oxygen in the atmosphere."""

EXAMPLE_DECK = {
    "title": EXAMPLE_TITLE,
    "guide": {
        "overview": (
            "These notes explain how plants convert light energy into glucose using "
            "carbon dioxide and water, where in the cell this happens, the two stages "
            "of the process, the factors that limit its rate, and why it matters for "
            "life on Earth."
        ),
        "sections": [
            {
                "heading": "What photosynthesis is",
                "content": (
                    "Photosynthesis is the process plants, algae and some bacteria use to turn "
                    "light energy into chemical energy. Carbon dioxide from the air and water from "
                    "the soil are combined into glucose, and oxygen is released as a by-product. "
                    "The word equation is: 6 CO2 + 6 H2O + light energy -> C6H12O6 + 6 O2. "
                    "Glucose is used by the plant as fuel and as a building material."
                ),
            },
            {
                "heading": "Where it happens",
                "content": (
                    "Photosynthesis happens inside chloroplasts, mainly in the mesophyll cells of "
                    "leaves. Chloroplasts contain chlorophyll, a green pigment that absorbs red and "
                    "blue light and reflects green light — which is why leaves look green. Gases "
                    "enter and leave the leaf through tiny pores called stomata."
                ),
            },
            {
                "heading": "The two stages",
                "content": (
                    "Stage 1: the light-dependent reactions, in the thylakoid membranes. Light splits "
                    "water molecules (photolysis), releasing oxygen, and the captured energy is stored "
                    "in ATP and NADPH. Stage 2: the light-independent reactions, also called the Calvin "
                    "cycle, in the stroma around the thylakoids. ATP and NADPH are used to fix carbon "
                    "dioxide into glucose. The second stage does not use light directly."
                ),
            },
            {
                "heading": "Limiting factors and why it matters",
                "content": (
                    "Three main factors limit the rate of photosynthesis: light intensity, carbon "
                    "dioxide concentration and temperature. Too little light or CO2 slows the process "
                    "down, and the enzymes involved work best at moderate temperatures. Photosynthesis "
                    "is the base of almost every food chain and produces practically all the oxygen in "
                    "the atmosphere — no other process does this on a comparable scale."
                ),
            },
        ],
        "glossary": [
            {"term": "Chlorophyll",
             "definition": "Green pigment in chloroplasts that absorbs red and blue light and reflects green light."},
            {"term": "Chloroplast",
             "definition": "The organelle in plant cells where both stages of photosynthesis happen."},
            {"term": "Stomata",
             "definition": "Tiny pores on leaves through which gases enter and leave."},
            {"term": "Photolysis",
             "definition": "The splitting of water molecules by light during the light-dependent reactions."},
            {"term": "Stroma",
             "definition": "The fluid inside a chloroplast where the Calvin cycle takes place."},
            {"term": "Calvin cycle",
             "definition": "The light-independent reactions that fix carbon dioxide into glucose."},
        ],
        "takeaways": [
            "Photosynthesis turns light energy into chemical energy stored in glucose.",
            "Word equation: 6 CO2 + 6 H2O + light energy -> C6H12O6 + 6 O2.",
            "Light-dependent reactions happen in the thylakoid membranes, the Calvin cycle in the stroma.",
            "The three limiting factors are light intensity, CO2 concentration and temperature.",
            "Photosynthesis is the base of almost every food chain and produces nearly all atmospheric oxygen.",
        ],
        "tips": [
            "Draw the word equation from memory until it comes automatically — it is a classic exam question.",
            "Link each stage to its location: thylakoid membranes for light reactions, stroma for the Calvin cycle.",
            "For each limiting factor, be ready to sketch or explain a rate graph: what rises, what plateaus and why.",
        ],
    },
    "flashcards": [
        {"question": "What is photosynthesis?",
         "answer": "Turning light energy into chemical energy (glucose) using CO2 and water"},
        {"question": "Word equation of photosynthesis",
         "answer": "6 CO2 + 6 H2O + light energy -> C6H12O6 + 6 O2"},
        {"question": "In which organelle does photosynthesis happen?",
         "answer": "Chloroplast"},
        {"question": "Green pigment that captures light",
         "answer": "Chlorophyll"},
        {"question": "Where do the light-dependent reactions happen?",
         "answer": "In the thylakoid membranes"},
        {"question": "Where does the Calvin cycle happen?",
         "answer": "In the stroma"},
        {"question": "What are the three limiting factors?",
         "answer": "Light intensity, CO2 concentration, temperature"},
        {"question": "Why is photosynthesis important?",
         "answer": "Base of almost every food chain; produces atmospheric oxygen"},
    ],
    "quiz": [
        {"type": "mc",
         "question": "In which organelle does photosynthesis mainly happen?",
         "options": ["Chloroplast", "Mitochondrion", "Nucleus", "Ribosome"],
         "correct_index": 0,
         "explanation": "Chloroplasts contain chlorophyll and host both stages of photosynthesis."},
        {"type": "tf",
         "question": "Photosynthesis converts light energy into chemical energy stored in glucose.",
         "answer": True,
         "explanation": "Light energy is captured and stored in the chemical bonds of glucose."},
        {"type": "fill",
         "question": "The green pigment that absorbs red and blue light is called ______.",
         "accepted": ["chlorophyll"],
         "explanation": "Chlorophyll reflects green light, which is why leaves look green."},
        {"type": "mc",
         "question": "Which gas do plants take in from the air for photosynthesis?",
         "options": ["Oxygen", "Nitrogen", "Carbon dioxide", "Hydrogen"],
         "correct_index": 2,
         "explanation": "Carbon dioxide is fixed into glucose during the Calvin cycle."},
        {"type": "match",
         "question": "Match each term with its meaning",
         "pairs": [
             {"left": "Chlorophyll", "right": "Pigment that absorbs red and blue light"},
             {"left": "Glucose", "right": "Sugar produced by photosynthesis"},
             {"left": "Stroma", "right": "Fluid where the Calvin cycle happens"},
             {"left": "Thylakoid", "right": "Membrane system of the light reactions"},
         ],
         "explanation": "Each structure and molecule has its own role in the two stages."},
        {"type": "tf",
         "question": "The Calvin cycle needs light to happen directly.",
         "answer": False,
         "explanation": "It uses ATP and NADPH made by the light reactions, so it does not use light directly."},
        {"type": "fill",
         "question": "Plants take in water for photosynthesis through their ______.",
         "accepted": ["roots", "root system"],
         "explanation": "Water travels from the roots to the leaves, where it is split by light."},
        {"type": "mc",
         "question": "Which of these is NOT a limiting factor of photosynthesis?",
         "options": ["Light intensity", "Soil colour", "Carbon dioxide concentration", "Temperature"],
         "correct_index": 1,
         "explanation": "The three limiting factors are light intensity, CO2 concentration and temperature."},
        {"type": "match",
         "question": "Match each stage or event with where it happens",
         "pairs": [
             {"left": "Light-dependent reactions", "right": "Thylakoid membranes"},
             {"left": "Calvin cycle", "right": "Stroma"},
             {"left": "Photolysis of water", "right": "Thylakoid membranes"},
             {"left": "Glucose production", "right": "Stroma"},
         ],
         "explanation": "Membranes handle the light stage; the fluid around them handles sugar building."},
        {"type": "mc",
         "question": "Why is photosynthesis important for ecosystems?",
         "options": [
             "It is the base of almost every food chain and produces oxygen",
             "It removes nitrogen from the atmosphere",
             "It produces carbon dioxide for animals",
             "It cools down the planet directly",
         ],
         "correct_index": 0,
         "explanation": "Producers capture energy that everything else depends on, and oxygen is a by-product."},
    ],
    "hangman": [
        {"clue": "Green pigment inside chloroplasts", "answer": "CHLOROPHYLL"},
        {"clue": "The organelle where photosynthesis happens", "answer": "CHLOROPLAST"},
        {"clue": "The sugar produced by photosynthesis", "answer": "GLUCOSE"},
        {"clue": "Gas released as a by-product", "answer": "OXYGEN"},
        {"clue": "Tiny pores on the leaf surface", "answer": "STOMATA"},
        {"clue": "Cycle that fixes carbon dioxide into sugar", "answer": "CALVIN"},
    ],
}
