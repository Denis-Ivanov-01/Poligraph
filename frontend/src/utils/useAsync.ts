import { useEffect, useState } from "react";

type AsyncState<T> = {
  data: T | null;
  error: string | null;
  loading: boolean;
};

export function useAsync<T>(loader: () => Promise<T>, deps: unknown[] = []): AsyncState<T> {
  const [state, setState] = useState<AsyncState<T>>({ data: null, error: null, loading: true });

  useEffect(() => {
    let active = true;
    setState({ data: null, error: null, loading: true });
    loader()
      .then((data) => {
        if (active) setState({ data, error: null, loading: false });
      })
      .catch((error: unknown) => {
        if (active) setState({ data: null, error: error instanceof Error ? error.message : "Unknown error", loading: false });
      });
    return () => {
      active = false;
    };
  }, deps);

  return state;
}
