"use client";

import { createContext, useContext, useState } from "react";

export type LangCode = "de" | "en" | "fr" | "it" | "es";

type LanguageContextValue = {
  language: LangCode;
  setLanguage: (lang: LangCode) => void;
};

const LanguageContext = createContext<LanguageContextValue>({
  language: "de",
  setLanguage: () => {},
});

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [language, setLanguage] = useState<LangCode>("de");
  return (
    <LanguageContext.Provider value={{ language, setLanguage }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  return useContext(LanguageContext);
}
