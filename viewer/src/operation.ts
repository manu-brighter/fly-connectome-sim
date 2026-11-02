// A pending parse keeps the previous recording visible, but must still block export.
export function createOperationGate() {
  let generation = 0, loading = false, exporting = false;
  return {
    get loading() { return loading; },
    get exporting() { return exporting; },
    beginLoad() {
      if (exporting) return null;
      loading = true;
      return ++generation;
    },
    isCurrentLoad(token: number | null) { return loading && token === generation; },
    endLoad(token: number | null) { if (loading && token === generation) loading = false; },
    beginExport() {
      if (loading || exporting) return false;
      exporting = true;
      return true;
    },
    endExport() { exporting = false; },
  };
}
