'use client';
import { useEffect, useState, type FormEvent } from 'react';
import { api } from '@/lib/api/client';

type Member = { id:string; username:string; display_name:string; membership_role:string; subjects:string[] };
type Teaching = { user_id:string; email:string; display_name:string; subject:string };

export default function ClassAdminPanel({ classroomId }: { classroomId:string }) {
  const [members,setMembers] = useState<Member[]>([]);
  const [teachers,setTeachers] = useState<Teaching[]>([]);
  const [email,setEmail] = useState('');
  const [subject,setSubject] = useState('');
  const [owner,setOwner] = useState('');
  const [notice,setNotice] = useState('');
  const [error,setError] = useState('');
  const [refresh,setRefresh] = useState(0);
  useEffect(()=>{
    api<Member[]>(`/classrooms/${classroomId}/members`).then(rows=>{setMembers(rows);setOwner('')}).catch(e=>setError(e.message));
    api<Teaching[]>(`/classrooms/${classroomId}/teachers`).then(setTeachers).catch(e=>setError(e.message));
  },[classroomId,refresh]);
  async function assign(e:FormEvent){e.preventDefault();setError('');setNotice('');try{await api(`/classrooms/${classroomId}/teachers`,{method:'POST',body:JSON.stringify({email,subject})});setEmail('');setSubject('');setNotice('Teacher assigned to the subject.');setRefresh(refresh+1)}catch(e){setError(e instanceof Error?e.message:'Could not assign teacher.')}}
  async function remove(userId:string,subjectName:string){try{await api(`/classrooms/${classroomId}/teachers/${userId}?subject=${encodeURIComponent(subjectName)}`,{method:'DELETE'});setRefresh(refresh+1)}catch(e){setError(e instanceof Error?e.message:'Could not remove subject assignment.')}}
  async function transfer(e:FormEvent){e.preventDefault();if(!owner)return;setError('');try{await api(`/classrooms/${classroomId}/ownership`,{method:'POST',body:JSON.stringify({new_owner_id:owner})});location.reload()}catch(e){setError(e instanceof Error?e.message:'Could not transfer ownership.')}}
  return <section className="card stack"><div><span className="pill">Class admin</span><h2 style={{marginTop:10}}>Class management</h2><p className="muted">Assign teachers by subject or hand this class to another member.</p></div>{error&&<p className="error">{error}</p>}{notice&&<p className="pill">{notice}</p>}
    <form className="grid" onSubmit={assign}><div className="field"><label>Teacher account email</label><input type="email" value={email} onChange={e=>setEmail(e.target.value)} required placeholder="They must sign in to Orbit first"/></div><div className="field"><label>Subject</label><input value={subject} onChange={e=>setSubject(e.target.value)} required minLength={2} placeholder="Mathematics"/></div><div className="field" style={{alignContent:'end'}}><button className="btn">Assign teacher</button></div></form>
    <div><h3>Subject assignments</h3><div className="list">{teachers.map(t=><div className="list-item" key={`${t.user_id}-${t.subject}`}><div><b>{t.display_name}</b><div className="muted">{t.email} · {t.subject}</div></div><button className="btn secondary" onClick={()=>remove(t.user_id,t.subject)}>Remove</button></div>)}{!teachers.length&&<div className="empty">No additional teachers assigned yet.</div>}</div></div>
    <form className="row" onSubmit={transfer}><div className="field" style={{flex:1}}><label>Transfer class ownership</label><select value={owner} onChange={e=>setOwner(e.target.value)}><option value="" disabled>Choose a class member</option>{members.map(m=><option value={m.id} key={m.id}>{m.display_name} · {m.membership_role.replace('_',' ')}</option>)}</select></div><button className="btn secondary" disabled={!owner}>Transfer ownership</button></form>
  </section>;
}
