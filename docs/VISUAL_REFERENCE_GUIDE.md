# Character Visual Reference Guide

## How to Use This Guide

When the pipeline detects speakers in your audio drama, it will ask you to define each character. Use the visual examples below as inspiration for your descriptions. The more specific your description, the more consistent and cinematic your final video will be.

---

## ARCHETYPE 1: The Wasted Aristocrat / Fallen Noble

**Visual Keywords:** Gaunt, pale, dark circles under eyes, expensive but rumpled clothing, trembling hands, hollow cheekbones, premature grey, dissipated beauty

**Reference Images:**

![Film noir detective shadowed face](https://kimi-web-img.moonshot.cn/img/media.istockphoto.com/3148d5d6d12bd9c0c03fafe0b48c0c1b9dd309d3.jpg)
*Shadowed figure in trench coat - the weight of secrets*

**Example Description for JSON:**
```json
{
  "LORD_ASHFORD": {
    "role": "antagonist",
    "age": "38",
    "gender": "male",
    "ethnicity": "Caucasian",
    "appearance": "Once handsome face now gaunt and sallow. Prominent cheekbones that cast hollow shadows. Dark purple-grey circles under pale blue eyes that water constantly. Thinning dark hair swept back to hide recession. Hands tremble visibly - long elegant fingers with nicotine stains. Premature grey at temples. Lips chapped and bitten. Skin has a waxy, translucent quality like old porcelain.",
    "clothing": "Expensive but threadbare navy velvet jacket with frayed cuffs. Crisp white shirt, now yellowed at collar. Silk cravat loosened and stained with wine. Signet ring on right pinky - family crest, worn smooth. Shoes polished but soles worn through.",
    "expression": "Hollow-eyed desperation masked by brittle aristocratic hauteur. Smiles too quickly, too widely - shows too many teeth. Eyes dart to exits, to windows, to shadows. Sweats despite cold rooms.",
    "voice": "Cultured baritone ruined by drink - cracks on high notes, drops to whisper mid-sentence. Laughs too loud, too long. Clears throat constantly.",
    "emotion": "desperate_arrogance",
    "distinguishing": "Trembling hands, watery pale eyes, frayed velvet jacket, signet ring, wine-stained cravat"
  }
}
```

---

## ARCHETYPE 2: The False Weakling / Deceptive Frailty

**Visual Keywords:** Deliberately fragile appearance, calculating eyes behind soft features, practiced vulnerability, hidden strength in posture, expensive simplicity

**Reference Images:**

![Soft features calculating gaze](https://kimi-web-img.moonshot.cn/img/p16-seeyou-useast8.capcutcdn-us.com/4d8aac68ffadad4c59e77e66929cd82ca1addc7a.image)
*Soft features, calculating gaze - vulnerability as weapon*

![Controlled intensity](https://kimi-web-img.moonshot.cn/img/assets.vofy.art/7992304b6e8ee0fa53210533cb2c4223807654e5.webp)
*Controlled intensity behind gentle appearance*

**Example Description for JSON:**
```json
{
  "MARGARET": {
    "role": "antagonist",
    "age": "26",
    "gender": "female",
    "ethnicity": "Caucasian",
    "appearance": "Deliberately fragile appearance - thin wrists, visible collarbones, pale skin that seems to bruise at a touch. Large grey-green eyes that fill with tears on command. Soft wavy hair always slightly disheveled. Small stature, 5'2", moves with practiced hesitation. But the collarbones are too prominent - maintained by discipline, not illness. The wrists, when she forgets herself, are steady as stone.",
    "clothing": "Simple cream silk blouses, always slightly wrinkled as if slept in. Pearl studs - real, inherited. No other jewelry. Dresses that look modest but are cut to suggest fragility. One ring: plain gold band, turned inward.",
    "expression": "Perpetually on the verge of tears. Lower lip trembles. Eyes widen at confrontation - but the pupils don't dilate. When she thinks no one watches, the softness hardens into something cold and patient. The trembling stops.",
    "voice": "Soft, breathy, frequently interrupted by small coughs. Speaks slowly, as if each word costs effort. But never stumbles over important words. Never hesitates before a lie.",
    "emotion": "calculated_vulnerability",
    "distinguishing": "Tear-ready eyes that never truly cry, steady hands she hides, gold band turned inward, practiced hesitation in movement"
  }
}
```

---

## ARCHETYPE 3: The Supreme Wastrel / Decadent Ruin

**Visual Keywords:** Bloated yet starving, sweat-sheen, ruined elegance, dissipated charisma, physical decay with expensive maintenance, the smell of money covering rot

**Reference Images:**

![Film noir atmosphere dissolution](https://kimi-web-img.moonshot.cn/img/learn.zoner.com/1cb97b428b2dbaac2473628eb64f83f05463f36b.jpg)
*Film noir atmosphere - the weight of dissolution*

![Shadow and smoke decay](https://kimi-web-img.moonshot.cn/img/learn.zoner.com/c263b11e55140deba077287bce2808ba9a891e34.jpg)
*Shadow and smoke - the texture of decay*

**Example Description for JSON:**
```json
{
  "COUNT_VORONIN": {
    "role": "antagonist",
    "age": "52",
    "gender": "male",
    "ethnicity": "Eastern European",
    "appearance": "Bloated yet somehow starving - flesh hangs on large frame like clothes on a scarecrow. Face puffy with drink but eyes sunken, burning. Grey-streaked black hair dyed badly, roots showing. Skin has a permanent sheen of sweat despite cold rooms. Teeth too white, too even - dentures. Veins on nose and cheeks ruptured into red spiderwebs. Hands swollen, rings embedded in flesh. Still physically imposing at 6'3" but moves with the careful deliberation of a man who knows his body is betraying him.",
    "clothing": "Impeccable tailoring that strains at the seams. Custom shirts with collar extended to hide neck wattles. Cufflinks heavy with ostentatious gems - rubies, emeralds. One lapel always slightly lower than the other - his tailor's revenge. Shoes handmade, resoled three times. Pockets always full - handkerchief, pills, small flask.",
    "expression": "Predatory bonhomie. Laughs with whole body, slaps backs, remembers everyone's name. But the eyes never participate - they assess, calculate, file away. When angered, the bonhomie drops instantly, replaced by something cold and efficient. No intermediate stage.",
    "voice": "Booming, theatrical, trained to fill rooms. But cracks appear - sudden hoarseness, wet coughs. When whispering, the voice becomes genuinely frightening - intimate, confessional, absolutely without warmth.",
    "emotion": "decadent_menace",
    "distinguishing": "Sweat-sheen despite cold, bad dye job showing grey roots, rings embedded in swollen fingers, theatrical bonhomie with dead eyes, booming voice with sudden hoarseness"
  }
}
```

---

## ARCHETYPE 4: The False Innocent / Corrupted Purity

**Visual Keywords:** Childlike features on adult face, too-wide eyes, practiced sweetness, something wrong in the proportions, beauty that unsettles

**Reference Images:**

![Digital overlay fracture](https://kimi-web-img.moonshot.cn/img/images.presentationgo.com/7d9c5e4cc3dea6a03dc6d65971816dbf8c6b798b.jpg)
*Digital overlay - the fracture between appearance and reality*

**Example Description for JSON:**
```json
{
  "ELISE": {
    "role": "antagonist",
    "age": "24",
    "gender": "female",
    "ethnicity": "Caucasian",
    "appearance": "Childlike features on adult face - round cheeks, small nose, large grey eyes that dominate the face. Blonde hair in loose ringlets, deliberately styled to look unstyled. 5'0", fine-boned, moves with light quick steps. But the proportions are slightly wrong - eyes too large for the face, giving her a doll-like quality that becomes uncanny in close-up. When she smiles, the smile reaches her eyes too perfectly, too completely.",
    "clothing": "Pastel colors exclusively - pale pink, baby blue, cream. High necklines, long sleeves, hems below knee. Modest, almost childish dresses. White gloves in public. One piece of jewelry: a silver locket, always closed, on a long chain.",
    "expression": "Perpetually surprised, perpetually delighted. Gasps at small things, claps hands softly. Tilts head to one side when listening - birdlike, predatory. The delight never wavers, even when discussing terrible things. The smile is fixed in place like a mask that has grown into the skin.",
    "voice": "High, light, girlish. Frequently rises to questions even when making statements. Uses diminutives, pet names. But the rhythm is too controlled - every giggle placed precisely, every gasp timed for effect. When alone, the voice drops an octave and the affect disappears entirely.",
    "emotion": "corrupted_innocence",
    "distinguishing": "Doll-like proportions, too-perfect smile, pastel clothing, closed silver locket, voice that drops an octave when alone"
  }
}
```

---

## ARCHETYPE 5: The Ruined Beauty / Faded Glory

**Visual Keywords:** Traces of former beauty in decay, maintained desperation, the ghost of elegance, cosmetic armor, beauty as battleground

**Example Description for JSON:**
```json
{
  "COUNTESS_DUBOIS": {
    "role": "supporting",
    "age": "55",
    "gender": "female",
    "ethnicity": "Caucasian",
    "appearance": "Traces of extraordinary beauty now fighting a losing war with time and drink. High cheekbones still prominent but skin starting to sag. Formerly striking green eyes now slightly yellowed, still expertly made up. Hair once auburn, now maintained with expensive dye that catches light wrong. Hands give everything away - liver spots, swollen knuckles, tremor she hides in gloves. Still moves with the unconscious grace of a woman who was once watched everywhere she went.",
    "clothing": "Expensive but slightly dated - last season's couture, or the season before. Colors too bright for her age, trying to recapture something. Jewelry heavy and inherited - diamonds that belonged to her mother, pearls that were her grandmother's. One modern piece: a smartwatch she checks obsessively.",
    "expression": "Fixed social smile that cracks when she drinks. Eyes that assess every room for threats or opportunities. Laughs at her own jokes too loudly. Touches her hair constantly - checking, adjusting, reassuring herself it's still there.",
    "voice": "Still musical, still trained, but the high notes have gone. Speaks quickly, as if afraid of interruption. Name-drops constantly. When alone, the voice becomes flat, tired, old.",
    "emotion": "desperate_nostalgia",
    "distinguishing": "Yellowed green eyes, trembling gloved hands, dated couture, inherited jewelry, checks hair constantly, voice that goes flat when alone"
  }
}
```

---

## Lighting & Mood Guide for These Archetypes

| Archetype | Key Light | Fill | Color Temp | Shadow Treatment |
|-----------|-----------|------|------------|------------------|
| Wasted Aristocrat | Single hard source from below | Minimal | Cold blue-white | Deep eye sockets, hollow cheeks |
| False Weakling | Soft window light | High | Warm neutral | Gentle, flattering, hides calculation |
| Supreme Wastrel | Overhead practical | Warm amber | Golden | Sweat-sheen, bloated features |
| False Innocent | Diffused, even | Very high | Soft pink-white | Flat, doll-like, no shadows |
| Ruined Beauty | Side light through curtains | Medium | Warm gold | Catches texture, shows age honestly |

---

## Shot Type Recommendations

| Archetype | Primary Shot | Secondary | Avoid |
|-----------|-------------|-----------|-------|
| Wasted Aristocrat | Close-up (eyes/hands) | Medium (slumped posture) | Wide shots showing vitality |
| False Weakling | Medium (full vulnerability display) | Insert (steady hands betraying) | Extreme close-ups showing cold eyes |
| Supreme Wastrel | Medium (imposing frame) | Close-up (sweat, decay) | Wide shots showing weakness |
| False Innocent | Medium (full costume, pose) | Close-up (doll eyes) | Low angles showing power |
| Ruined Beauty | Medium (grace in decay) | Close-up (traces of former beauty) | Harsh light showing all damage |

---

## Quick Reference: Description Quality Checklist

Before saving your characters.json, verify each description has:

- [ ] **Specific physical details** (not "handsome" but "high cheekbones, broken nose healed crooked")
- [ ] **Clothing with story** (not "suit" but "father's suit, taken in at waist, cuffs frayed")
- [ ] **Resting expression** (what does the face do when they think no one watches?)
- [ ] **Contradictions** (the weakling's steady hands, the wastrel's cultured voice)
- [ ] **Movement habits** (how they enter rooms, how they sit, what they touch)
- [ ] **Voice-to-visual bridge** (how speech patterns suggest physical presence)
- [ ] **Decay markers** (what's failing, what's maintained, what's given up on)
- [ ] **Lighting hints** (how should this face be lit for maximum story impact?)
