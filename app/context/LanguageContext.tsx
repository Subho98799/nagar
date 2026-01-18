import React, { createContext, useContext, useEffect, useState } from "react";
import type { Language } from "~/lib/i18n";

type LangCtx = {
  lang: Language;
  toggle: () => void;
};

const LanguageContext = createContext<LangCtx | null>(null);

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLang] = useState<Language>("en");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const saved = localStorage.getItem("lang");
    if (saved === "en" || saved === "hi") {
      setLang(saved);
    }
    setMounted(true);
  }, []);

  const toggle = () => {
    setLang((prev) => {
      const next = prev === "en" ? "hi" : "en";
      localStorage.setItem("lang", next);
      return next;
    });
  };

  if (!mounted) {
    return null;
  }

  return (
    <LanguageContext.Provider value={{ lang, toggle }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const ctx = useContext(LanguageContext);
  if (!ctx) {
    throw new Error("LanguageProvider missing");
  }
  return ctx;
}
