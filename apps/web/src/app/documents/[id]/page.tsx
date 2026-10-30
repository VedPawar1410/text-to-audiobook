import { Suspense } from "react";
import { DirectorsNotes, NotesSkeleton } from "@/components/notes/directors-notes";

// Not async on purpose (Cache Components): the page shell stays static and instant;
// only the part that needs the document id waits, inside <Suspense>.
export default function DocumentPage({ params }: { params: Promise<{ id: string }> }) {
  return (
    <main className="mx-auto w-full max-w-5xl px-4 pt-32 pb-24 md:px-8 md:pt-40">
      <Suspense fallback={<NotesSkeleton />}>
        <DirectorsNotes params={params} />
      </Suspense>
    </main>
  );
}
