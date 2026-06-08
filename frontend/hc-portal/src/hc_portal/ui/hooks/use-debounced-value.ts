import { useEffect, useState } from "react";

/**
 * Returns a value that lags `value` by `delay` ms.
 *
 * Used by the search inputs to avoid hammering the BFF on every keystroke —
 * the page's data query keys off the *debounced* value, so a fast typist
 * sends one request, not ten.
 */
export function useDebouncedValue<T>(value: T, delay = 300): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return debounced;
}
