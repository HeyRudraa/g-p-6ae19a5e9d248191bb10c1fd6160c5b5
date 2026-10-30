'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api/client';
import type { Assignment } from '@/lib/api/types';

function formatDueDate(dueAt: string | null): string {
  if (dueAt === null) return 'No due date';
  return new Date(dueAt).toLocaleString();
}

export default function AssignmentDetail({ id }: { id: string }) {
  const [assignment, setAssignment] = useState<Assignment | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [text, setText] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [message, setMessage] = useState('');

  useEffect(() => {
    api<Assignment>(`/assignments/${id}`)
      .then(setAssignment)
      .catch((error: unknown) => {
        setMessage(error instanceof Error ? error.message : 'Could not load assignment.');
      });
  }, [id]);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!assignment) return;

    const data = new FormData();
    data.set('text_response', text);
    data.set('answers_json', JSON.stringify(answers));
    if (file) data.set('file', file);

    try {
      await api(`/assignments/${id}/submissions`, { method: 'POST', body: data });
      setMessage('Your work was submitted.');
    } catch (error: unknown) {
      setMessage(error instanceof Error ? error.message : 'Could not submit work.');
    }
  }

  if (!assignment) {
    return <div className="empty">{message || 'Loading assignment…'}</div>;
  }

  return (
    <>
      <section className="hero">
        <a className="link" href="/orbit/assignments">← Assignments</a>
        <h1 style={{ marginTop: 14 }}>{assignment.title}</h1>
        <p className="muted">
          {assignment.points} points · due {formatDueDate(assignment.due_at)}
        </p>
        <p>{assignment.instructions}</p>
      </section>

      <form className="card stack" onSubmit={submit}>
        <h2>Your submission</h2>
        {assignment.questions.map((question, questionIndex) => (
          <fieldset className="card" key={question.id}>
            <legend>{questionIndex + 1}. {question.prompt}</legend>
            {question.choices.map((choice, choiceIndex) => {
              const answer = String.fromCharCode(65 + choiceIndex);
              return (
                <label className="row" key={choice} style={{ padding: 8 }}>
                  <input
                    type="radio"
                    name={question.id}
                    checked={answers[question.id] === answer}
                    onChange={() => setAnswers({ ...answers, [question.id]: answer })}
                  />
                  {choice}
                </label>
              );
            })}
          </fieldset>
        ))}

        <div className="field">
          <label htmlFor="written-response">Written response</label>
          <textarea
            id="written-response"
            rows={6}
            value={text}
            onChange={(event) => setText(event.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="assignment-file">Attach work (PDF, image, text, DOCX)</label>
          <input
            id="assignment-file"
            type="file"
            accept=".pdf,.jpg,.jpeg,.png,.txt,.docx"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          />
        </div>
        <button className="btn" type="submit">Submit assignment</button>
        {message && (
          <p className={message.startsWith('Your') ? 'pill' : 'error'}>{message}</p>
        )}
      </form>
    </>
  );
}
