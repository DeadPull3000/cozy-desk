'use client';

import { useEffect, useState } from 'react';
import { BookOpen, Check, X, Calendar as CalendarIcon, Clock, Mail } from 'lucide-react';
import { format } from 'date-fns';

type Candidate = {
  id: number;
  title: string;
  course: string | null;
  source: string;
  deadline: string | null;
  confidence: number;
};

export default function Home() {
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('http://localhost:8000/api/candidates/pending')
      .then((res) => res.json())
      .then((data) => {
        setCandidates(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Failed to fetch candidates", err);
        setLoading(false);
      });
  }, []);

  const handleAction = async (id: number, action: 'APPROVED' | 'REJECTED') => {
    // Optimistic UI update - remove the note from the desk immediately
    setCandidates((prev) => prev.filter((c) => c.id !== id));
    
    await fetch(`http://localhost:8000/api/candidates/${id}/status`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: action }),
    });
  };

  return (
    <main className="max-w-3xl mx-auto px-6 py-16 min-h-screen">
      
      {/* Header Section */}
      <header className="mb-16">
        <h1 className="font-serif text-4xl text-espresso mb-2 tracking-tight">
          Good evening, Vaishnavi.
        </h1>
        <p className="text-warm-taupe text-lg font-light flex items-center gap-2">
          {candidates.length > 0 
            ? `I found ${candidates.length} thing${candidates.length > 1 ? 's' : ''} that might belong on your calendar.` 
            : "Your desk is perfectly clear."}
        </p>
      </header>

      {/* Things I Found Section */}
      <section>
        <h2 className="text-sm font-semibold tracking-widest uppercase text-warm-taupe mb-6 border-b border-oat-beige pb-2 flex items-center gap-2">
          <Mail className="w-4 h-4" /> Inbox
        </h2>
        
        {loading ? (
          <p className="text-warm-taupe text-sm italic">Organizing your desk...</p>
        ) : (
          <div className="space-y-6">
            {candidates.map((candidate) => (
              <div key={candidate.id} className="card-stationery p-6 relative group">
                
                {/* Confidence indicator / little tag */}
                <div className="absolute -top-3 right-6 bg-warm-ivory border border-oat-beige text-[10px] uppercase tracking-wider text-warm-taupe px-3 py-1 rounded-full shadow-sm">
                  {Math.round(candidate.confidence * 100)}% Match
                </div>

                <div className="flex items-start gap-4 mb-5">
                  <div className="bg-warm-ivory p-3 rounded-xl border border-oat-beige text-terracotta shrink-0">
                    <BookOpen className="w-5 h-5" />
                  </div>
                  <div>
                    {candidate.course && (
                      <p className="text-xs font-medium text-warm-taupe mb-1 flex items-center gap-1">
                        {candidate.course}
                      </p>
                    )}
                    <h3 className="font-serif text-xl text-espresso leading-snug">
                      {candidate.title}
                    </h3>
                  </div>
                </div>

                <div className="bg-warm-ivory/50 rounded-lg p-4 mb-6 border border-oat-beige/50 space-y-2">
                  {candidate.deadline && (
                    <div className="flex items-center gap-2 text-sm text-espresso">
                      <CalendarIcon className="w-4 h-4 text-terracotta" />
                      <span>Due {format(new Date(candidate.deadline), 'MMMM do')}</span>
                      <span className="text-warm-taupe mx-1">·</span>
                      <Clock className="w-4 h-4 text-warm-taupe" />
                      <span className="text-warm-taupe">{format(new Date(candidate.deadline), 'h:mm a')}</span>
                    </div>
                  )}
                  <p className="text-xs text-warm-taupe font-medium pt-1">
                    Found in {candidate.source}
                  </p>
                </div>

                <div className="flex items-center gap-3">
                  <button 
                    onClick={() => handleAction(candidate.id, 'APPROVED')}
                    className="flex-1 bg-sage-green/10 hover:bg-sage-green/20 text-sage-green transition-colors border border-sage-green/20 py-2.5 rounded-lg text-sm font-medium flex items-center justify-center gap-2"
                  >
                    <Check className="w-4 h-4" /> Add to Calendar
                  </button>
                  <button 
                    onClick={() => handleAction(candidate.id, 'REJECTED')}
                    className="px-5 py-2.5 bg-warm-ivory hover:bg-oat-beige text-warm-taupe transition-colors border border-oat-beige rounded-lg text-sm font-medium flex items-center gap-2"
                  >
                    <X className="w-4 h-4" /> Ignore
                  </button>
                </div>
              </div>
            ))}
            
            {candidates.length === 0 && !loading && (
              <div className="text-center py-16 bg-soft-cream rounded-[16px] border border-oat-beige border-dashed">
                <p className="text-warm-taupe">You are all caught up.</p>
              </div>
            )}
          </div>
        )}
      </section>
    </main>
  );
}

