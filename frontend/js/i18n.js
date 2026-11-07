// English / नेपाली for the page's fixed text (elements with data-i18n). Text written by the data files or the
// scripts (measurements, warnings, notes) stays in English, and the Nepali page says so (lang.note).
const STORE_KEY = "spherex-blink-lang";

export const NE = {
  "nav.explore": "अन्वेषण",
  "nav.about": "बारेमा",
  "lang.note": "पृष्ठका शीर्षक, बटन र व्याख्याहरू नेपालीमा छन्। नापिएका अङ्क, चेतावनी र विवरणहरू अहिले अङ्ग्रेजीमै छन्।",
  "hero.eyebrow": "NASA SPHEREx का तस्बिरहरू, 0.75–5.0 µm",
  "hero.title": "इन्फ्रारेड आकाश बदलिएको हेर्नुहोस्।",
  "hero.sub": "ताराको नाम वा आकाशको स्थान लेख्नुहोस्, अनि आकाशको त्यो भागका SPHEREx तस्बिरहरू एकपछि अर्को अवलोकन गर्दै पल्टाउनुहोस्।",
  "search.title": "1. आकाशको एउटा भाग छान्नुहोस्",
  "search.query": "ताराको नाम वा स्थान (RA, Dec)",
  "search.go": "जानुहोस्",
  "search.help": "नाम (SIMBAD मा खोजिन्छ), <code>17h57m47s +04d46m06s</code>, <code>17:57:47 +04:46:06</code> वा डिग्रीमा <code>269.446 4.768</code> लेख्न सकिन्छ।",
  "search.fov": "दृश्य क्षेत्र:",
  "search.fov_help": "फ्लिपबुकले देखाउने वर्गको आकार (1–15 आर्कमिनेट)।",
  "search.det": "SPHEREx डिटेक्टर",
  "search.det_help": "फ्लिपबुकले कुन तरङ्गदैर्घ्य दायरा देखाउँछ।",
  "targets.title": "2. वा आधिकारिक लक्ष्यबाट सुरु गर्नुहोस्",
  "selection.title": "3. तपाईंको स्थान",
  "selection.none": "अहिलेसम्म कुनै स्थान छानिएको छैन। लेख्नुहोस्, लक्ष्य छान्नुहोस्, वा आकाश नक्सामा क्लिक गर्नुहोस्।",
  "map.title": "आकाश नक्सा",
  "map.background": "पृष्ठभूमि",
  "map.help": "सार्न तान्नुहोस्, जुम गर्न स्क्रोल गर्नुहोस्, स्थान छान्न क्लिक गर्नुहोस्। सेतो वर्ग दृश्य क्षेत्र हो।",
  "flip.title": "SPHEREx फ्लिपबुक",
  "flip.cautions": "आफ्नो आँखामा भरोसा गर्नुअघि",
  "flip.mode_play": "चलाउनुहोस्",
  "flip.mode_blink": "2 अवलोकन ब्लिङ्क गर्नुहोस्",
  "flip.visit": "अवलोकन",
  "flip.speed": "गति",
  "flip.loop": "दोहोर्‍याउनुहोस्",
  "flip.visit_a": "अवलोकन A",
  "flip.visit_b": "अवलोकन B",
  "flip.tombaugh": "सन् 1930 मा क्लाइड टमबाहले जस्तै: एउटै आकाशका दुई तस्बिर छिटो-छिटो साटिन्छन्, र सरेको वा बदलिएको कुरा उफ्रेर देखिन्छ।",
  "flip.flags": "फ्ल्याग गरिएका पिक्सेल रातोमा देखाउनुहोस्",
  "flip.gaia": "Gaia DR3 चिन्हहरू",
  "flip.stars": "ताराहरू",
  "sci.toggle": "वैज्ञानिक दृश्य: कच्चा पिक्सेल र फ्ल्यागहरू",
  "sci.title": "वैज्ञानिक दृश्य: कच्चा पिक्सेल र फ्ल्यागहरू",
  "sci.intro": "फ्लिपबुक फ्रेमपछाडिको एउटा एक्सपोजरका सबै डिटेक्टर पिक्सेल, NASA IRSA ले दिएजस्तै, तिनको FLAGS मानले के भन्छ त्यसअनुसार रङ लगाइएका। पिक्सेलको स्थान, मान, तरङ्गदैर्घ्य र हरेक फ्ल्याग बिट हेर्न त्यसमा पोइन्टर राख्नुहोस् (वा एरो कुञ्जी प्रयोग गर्नुहोस्)।",
  "sci.exposure": "एक्सपोजर",
  "sci.by_flags": "फ्ल्यागको प्रकार",
  "sci.by_brightness": "चमक",
  "sci.grid": "पिक्सेल ग्रिड",
  "sci.bits": "यो फाइलमा परिभाषित फ्ल्याग बिटहरू",
  "sci.bits_help": "प्रत्येक पिक्सेलको FLAGS मान एउटा 32-बिट पूर्णाङ्क हो: सेट भएका हरेक बिटको 2<sup>bit</sup> को योग। नाम र अर्थ फाइलकै हेडरबाट आउँछन्। त्यसका पिक्सेल हाइलाइट गर्न नाममा क्लिक गर्नुहोस्।",
  "sci.how": "यसलाई कसरी पढ्ने",
  "iv.toggle": "एउटै अवलोकनभित्र: एक-एक एक्सपोजर (घण्टौँको फरकमा)",
  "iv.title": "एउटै अवलोकनभित्र: एक-एक एक्सपोजर",
  "iv.intro": "फ्लिपबुक फ्रेमले SPHEREx ले घण्टौँदेखि दिनौँको फरकमा लिएका धेरै एक्सपोजर जोड्छ। यहाँ ती एउटै ग्रिडमा मिलाएर एक-एक गरी देखाइएका छन्: क्षुद्रग्रह एउटै अवलोकनभित्रै सरेको देखिन्छ, तारा सर्दैन। वर्गहरूले प्रत्येक एक्सपोजरको समयमा NASA JPL ले फ्रेमभित्र राखेका ज्ञात क्षुद्रग्रह र धूमकेतु देखाउँछन्।",
  "iv.exposure": "एक्सपोजर",
  "iv.picture": "तस्बिर",
  "iv.residual": "अवलोकनको मध्यिका घटाएर",
  "iv.known": "ज्ञात क्षुद्रग्रह र धूमकेतु (NASA JPL)",
  "iv.cautions": "सरेको दागमा भरोसा गर्नुअघि",
  "rec.title": "यी दुई अवलोकनमा दाग खोज्ने औजार कत्तिको राम्रो छ?",
  "rec.help": "थाहा भएको चमकका नक्कली सर्ने ताराहरू यी दुई वास्तविक फ्रेमका प्रतिलिपिमा थपिए, र उही फरक तथा 5σ दाग खोजी फेरि चलाइयो। यसले यहाँ कति धमिलो सर्ने वस्तु पनि भेटिन्छ भन्ने बताउँछ।",
  "rec.how": "यो कसरी मापन गरियो, र यसका सीमाहरू",
  "files.gif": "GIF डाउनलोड गर्नुहोस्",
  "files.originals": "NASA IRSA मा मूल फाइलहरू",
  "ask.title": "यो दृश्यबारे सोध्नुहोस्",
  "ask.badge": "AI व्याख्याता · Google Gemini",
  "ask.help": "यस पृष्ठले के देखाउँछ भनेर सजिलो भाषामा सोध्नुहोस्। Gemini ले यस दृश्यकै डेटा (तलका प्यानलहरू पछाडिका उही फाइलहरू) बाट मात्र जवाफ दिन्छ, प्रयोग गरेका तथ्यहरूको नाम दिन्छ, र यो औजारले जवाफका हरेक अङ्क ती तथ्यसँग जाँच्छ। यसले तस्बिरहरू हेर्न सक्दैन, र दाग कहिल्यै आविष्कार होइन।",
  "ask.q1": "म के हेरिरहेको छु?",
  "ask.q2": "के यो तारा साँच्चै सर्‍यो?",
  "ask.q3": "के यी दागहरू वास्तविक हुन्?",
  "ask.q4": "यहाँ कति धमिलो सर्ने वस्तु भेटिन सक्छ?",
  "ask.q5": "के यो प्लानेट X हो?",
  "ask.submit": "सोध्नुहोस्",
  "tl.title": "SPHEREx ले यहाँ कहिले हेर्‍यो",
  "tl.caption": "यस स्थानका सबै SPHEREx तस्बिरहरू, प्रत्येक डिटेक्टरको एउटा पङ्क्ति। प्रत्येक पातलो रेखा एउटा तस्बिर हो; प्रत्येक खैरो पट्टी एउटा अवलोकन हो। ▼ = फ्लिपबुकमा देखाइएका अवलोकनहरू। त्यो डिटेक्टर हेर्न पङ्क्तिमा क्लिक गर्नुहोस्।",
  "proof.title": "प्रमाण",
  "proof.motion": "Gaia DR3 सँग गतिको तुलना",
  "proof.data": "यो केमा आधारित छ",
  "diff.title": "पहिले / पछि / फरक",
  "diff.a": "पहिले (A)",
  "diff.b": "पछि (B)",
  "diff.closest": "सबैभन्दा नजिकका तरङ्गदैर्घ्य",
  "diff.fainter": "−5σ B मा धमिलो",
  "diff.brighter": "+5σ B मा चम्किलो",
  "diff.striped": "कुनै एक अवलोकनमा फ्ल्याग गरिएको वा मान नभएको",
  "diff.cautions": "रङ्गीन दागमा भरोसा गर्नुअघि",
  "diff.help": "दुवै फोटो प्यानलले फ्लिपबुकको एउटै चमक स्केल प्रयोग गर्छन्। फरक = (B − A − आकाशको परिवर्तन) / √(σ<sub>A</sub>² + σ<sub>B</sub>²), σ SPHEREx का VARIANCE नक्साबाट, <code>backend/app/diff.py</code> ले बनाएको। माथिको ब्लिङ्क नै इमानदार एनिमेसन हो; अवलोकनहरूबीच कुनै फेड छैन।",
  "spot.title": "5σ भन्दा माथिका दागहरू",
  "spot.help": "A र B बीच 5σ भन्दा बढी बदलिएका पिक्सेलका समूहहरू, सबैभन्दा बलियो पहिले, फरक प्यानलमा अङ्कित। दाग हेर्ने ठाउँ हो, आविष्कार होइन: धेरैजसो ताराहरू, उपकरणका त्रुटि वा नोइजबाट आउँछन्।",
  "spot.else": "यसलाई अरू केले व्याख्या गर्न सक्छ",
  "spot.confirm": "यसलाई के कुराले पुष्टि गर्छ",
  "spot.jpl": "ज्ञात क्षुद्रग्रह र धूमकेतु जाँच्नुहोस् (NASA JPL)",
  "lc.title": "प्रकाश वक्र",
  "lc.back": "लक्ष्यमा फर्कनुहोस्",
  "lc.click": "यसको सट्टा मापन गर्न फ्लिपबुकको कुनै पनि पिक्सेलमा क्लिक गर्नुहोस् (data API चाहिन्छ)।",
  "lc.time_caption": "समयअनुसार प्रत्येक एक्सपोजरको चमक। रङ = त्यो एक्सपोजरले यस स्थानमा देखेको तरङ्गदैर्घ्य (<span class=\"lc-blue\">छोटो</span> देखि <span class=\"lc-red\">लामो</span>); खोक्रो = घेराभित्र फ्ल्याग गरिएको पिक्सेल वा 5σ भन्दा धमिलो। एउटै अवलोकनका बिन्दुहरू माथि-तल फैलिनुको मुख्य कारण फरक तरङ्गदैर्घ्य हो, तारा बदलिएको होइन।",
  "lc.wl_caption": "उही एक्सपोजरहरू तरङ्गदैर्घ्यअनुसार, प्रत्येक अवलोकनको एउटा रङ। जहाँ दुई अवलोकन तरङ्गदैर्घ्यमा खप्टिन्छन्, त्यहाँ तिनका रङबीचको अन्तर चमकमा आएको परिवर्तन हो।",
  "lc.compared": "एउटै तरङ्गदैर्घ्यमा तुलना गरिएका अवलोकनहरू",
  "lc.cautions": "परिवर्तनमा भरोसा गर्नुअघि",
  "spec.title": "स्पेक्ट्रम",
  "spec.caption": "फ्रेम भएका सबै डिटेक्टरबाट तरङ्गदैर्घ्यअनुसार चमक, प्रत्येक अवलोकनको एउटा रङ। SPHEREx का छ वटा डिटेक्टरले एउटै आकाश एकै समयमा हेर्छन्, त्यसैले एउटा अवलोकनले तिनको पूरा दायरा समेट्छ। धर्सा रेखा: एउटा डिटेक्टर सकिएर अर्को सुरु हुने ठाउँ। खोक्रो = घेराभित्र फ्ल्याग गरिएको पिक्सेल वा 5σ भन्दा धमिलो।",
  "spec.detectors": "डिटेक्टरहरू",
  "spec.cautions": "आकार पढ्नुअघि",
};

const TITLES = { en: "SPHEREx Blink: see the infrared sky change", ne: "SPHEREx Blink: इन्फ्रारेड आकाश बदलिएको हेर्नुहोस्" };

/** Put every data-i18n element in `lang` ("en" or "ne"); the English text is kept on first use. */
export function applyLanguage(lang, root = document) {
  for (const el of root.querySelectorAll("[data-i18n]")) {
    if (el.dataset.en === undefined) el.dataset.en = el.innerHTML;
    const ne = NE[el.dataset.i18n];
    el.innerHTML = lang === "ne" && ne ? ne : el.dataset.en;
  }
  const note = root.getElementById ? root.getElementById("lang-note") : null;
  if (note) note.hidden = lang !== "ne";
  if (root.documentElement) {
    root.documentElement.lang = lang;
    root.title = TITLES[lang] || TITLES.en;
  }
}

export function savedLanguage(storage = globalThis.localStorage) {
  try {
    return storage && storage.getItem(STORE_KEY) === "ne" ? "ne" : "en";
  } catch {
    return "en";
  }
}

/** The header button: shows the other language's name, switches and remembers. */
export function createLanguageToggle(button, storage = globalThis.localStorage) {
  let lang = savedLanguage(storage);
  function set(next) {
    lang = next;
    applyLanguage(lang);
    button.textContent = lang === "ne" ? "English" : "नेपाली";
    button.lang = lang === "ne" ? "en" : "ne";
    try { storage && storage.setItem(STORE_KEY, lang); } catch { /* private mode */ }
  }
  button.addEventListener("click", () => set(lang === "ne" ? "en" : "ne"));
  if (lang === "ne") set("ne");
  return { get: () => lang };
}
