// Synthetic fixture — intentionally contains stub patterns for the audit harness.

import { Button } from "../components/button";

export default function HomePage() {
  return (
    <main>
      <h1>Welcome</h1>
      {/* HIGH: labelled action button with empty onClick */}
      <Button onClick={() => {}}>Share results</Button>

      {/* HIGH: handler that "abandons" without server call */}
      <Button
        onClick={() => {
          // TODO: wire abandon flow to server
        }}
      >
        Abandon session
      </Button>
    </main>
  );
}
