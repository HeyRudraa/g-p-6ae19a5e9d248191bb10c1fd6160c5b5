'use client';
import { useEffect, useState, type ReactNode } from 'react';
import { onAuthStateChanged, signOut } from 'firebase/auth';
import { auth } from '@/lib/firebase/client';
import { api } from '@/lib/api/client';
import type { Classroom, User } from '@/lib/api/types';

const links = [
  ['/orbit', 'Overview'], ['/orbit/classrooms', 'Classrooms'], ['/orbit/assignments', 'Assignments'],
  ['/orbit/grades', 'My grades'], ['/orbit/coding', 'Coding ground'], ['/orbit/study', 'Study space'],
  ['/orbit/tools', 'Academic tools'], ['/orbit/profile', 'Profile'],
];

export default function Workspace({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [canManage, setCanManage] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!auth) {
      setError('Set Firebase settings in frontend/.env.local to enable your workspace.');
      setLoading(false);
      return;
    }
    return onAuthStateChanged(auth, async (firebaseUser) => {
      if (!firebaseUser) { location.href = '/login'; return; }
      try {
        await firebaseUser.getIdToken();
        if (!firebaseUser.emailVerified) { location.href = '/verify-email'; return; }
        const profile = await api<User>('/auth/me');
        setUser(profile);
        const classes = await api<Classroom[]>('/classrooms');
        setCanManage(classes.some((c) => c.member_role === 'teacher' || c.member_role === 'class_admin'));
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Unable to load your Orbit profile.');
      } finally { setLoading(false); }
    });
  }, []);

  if (loading) return <div className="main">Loading your Orbit space…</div>;
  if (error) return <div className="main"><div className="card"><h2>Orbit needs setup</h2><p className="muted">{error}</p><a href="/login" className="btn">Back to sign in</a></div></div>;
  if (user && !user.onboarding_completed) return <Onboarding user={user} onDone={setUser} />;

  const visibleLinks = canManage ? [...links, ['/orbit/teacher', 'Teacher center']] : links;
  return <div className="shell"><aside className="side">
    <a className="brand" href="/orbit">orbit<i>.</i></a>
    <nav className="nav">{visibleLinks.map(([href, label]) => <a key={href} href={href} className={location.pathname === href ? 'active' : ''}>{label}</a>)}</nav>
    <div className="side-bottom"><div className="row"><div className="avatar">{user?.display_name?.[0] || 'O'}</div><div><b>{user?.display_name || user?.username}</b><div className="muted">Orbit member</div></div></div>
      <button className="btn secondary block" onClick={() => auth && signOut(auth)}>Sign out</button>
    </div>
  </aside><main className="main"><div className="topbar"><span className="muted">Your learning space</span><div className="row"><span className="muted">{user?.display_name || user?.username}</span><div className="avatar">{user?.display_name?.[0] || 'O'}</div></div></div>{children}</main></div>;
}

function Onboarding({ user, onDone }: { user: User; onDone: (user: User) => void }) {
  const [name, setName] = useState(user.display_name || '');
  const [handle, setHandle] = useState(user.username || '');
  const [error, setError] = useState('');
  async function save() {
    try {
      const result = await api<User>('/auth/me', { method: 'PATCH', body: JSON.stringify({ display_name: name, username: handle, avatar_id: 'orbit', onboarding_completed: true }) });
      onDone(result);
    } catch (e) { setError(e instanceof Error ? e.message : 'Could not save your profile.'); }
  }
  return <div className="auth-wrap"><section className="auth-art"><a className="brand">orbit<i>.</i></a><div><span className="orbit-visual">◉</span><h1>Make this space yours.</h1><p>Choose a display name and username so your classmates can recognize you.</p></div><small>One quick step to get started.</small></section><section className="auth-panel"><div className="auth-card"><h2>Set up your profile</h2><p className="sub">You can update this any time.</p>{error && <p className="error">{error}</p>}<div className="field"><label>Display name</label><input value={name} onChange={(e) => setName(e.target.value)} /></div><div className="field"><label>Username</label><input value={handle} onChange={(e) => setHandle(e.target.value)} /></div><button className="btn block" onClick={save}>Continue to Orbit</button></div></section></div>;
}
