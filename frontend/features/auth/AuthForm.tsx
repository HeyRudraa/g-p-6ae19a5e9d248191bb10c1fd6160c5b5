'use client';
import { FormEvent, useState } from 'react';
import { confirmPasswordReset, createUserWithEmailAndPassword, GoogleAuthProvider, sendEmailVerification, sendPasswordResetEmail, signInWithEmailAndPassword, signInWithPopup, updateProfile } from 'firebase/auth';
import { auth, firebaseConfigured } from '@/lib/firebase/client';
export default function AuthForm({ mode }: {mode:'login'|'signup'|'forgot'|'reset'|'verify'}) {
 const [error,setError]=useState(''); const [busy,setBusy]=useState(false); const [done,setDone]=useState(false);
 async function submit(e:FormEvent<HTMLFormElement>){e.preventDefault();setError('');setBusy(true);const f=new FormData(e.currentTarget);const email=String(f.get('email')||'');const password=String(f.get('password')||'');try{
  if(!auth||!firebaseConfigured)throw new Error('Add your Firebase web settings to frontend/.env.local to enable sign-in.');
  if(mode==='signup'){const cred=await createUserWithEmailAndPassword(auth,email,password);await updateProfile(cred.user,{displayName:String(f.get('name')||'')});await sendEmailVerification(cred.user);location.href='/verify-email';}
  else if(mode==='login'){await signInWithEmailAndPassword(auth,email,password);location.href='/orbit';}
  else if(mode==='forgot'){await sendPasswordResetEmail(auth,email,{url:`${location.origin}/reset-password`,handleCodeInApp:false});setDone(true);}
  else if(mode==='verify'){if(!auth.currentUser)throw new Error('Sign in first to verify your email.');await sendEmailVerification(auth.currentUser);setDone(true);}
  else if(mode==='reset'){const code=new URLSearchParams(location.search).get('oobCode');if(!code)throw new Error('This reset link is missing or expired. Request a new one.');await confirmPasswordReset(auth,String(code),password);setDone(true);}
 }catch(ex){setError(ex instanceof Error?ex.message:'Something went wrong.');}finally{setBusy(false)}}
 async function googleSignIn(){setError('');setBusy(true);try{if(!auth||!firebaseConfigured)throw new Error('Add your Firebase web settings to frontend/.env.local to enable sign-in.');await signInWithPopup(auth,new GoogleAuthProvider());location.href='/orbit'}catch(ex){setError(ex instanceof Error?ex.message:'Google sign-in failed.')}finally{setBusy(false)}}
 const title={login:'Welcome back',signup:'Create your account',forgot:'Reset your password',reset:'Choose a new password',verify:'Check your inbox'}[mode];
 if(done)return <div className="card"><h2>{mode==='forgot'?'Email sent':mode==='verify'?'Verification sent':'You’re all set'}</h2><p className="muted">{mode==='forgot'?'If an account exists for this email, a reset link is on the way.':mode==='verify'?'Open the verification link, then return to Orbit and sign in.':'Continue to your Orbit workspace.'}</p><a className="btn" href="/login">Back to sign in</a></div>;
 return <form className="auth-card" onSubmit={submit}><h2>{title}</h2><p className="sub">{mode==='signup'?'One account for your learning space.':mode==='verify'?'We sent a link to your email address.':''}</p>{error&&<p className="error">{error}</p>}
 {mode==='signup'&&<div className="field"><label>Your name</label><input name="name" required autoComplete="name"/></div>}
 {['login','signup','forgot'].includes(mode)&&<div className="field"><label>Email address</label><input name="email" type="email" required autoComplete="email"/></div>}
 {['login','signup','reset'].includes(mode)&&<div className="field"><label>Password</label><input name="password" type="password" minLength={8} required autoComplete={mode==='login'?'current-password':'new-password'}/></div>}
 {mode==='verify'&&<p className="muted">You’ll need to verify your email before using Orbit.</p>}
 <button className="btn block" disabled={busy}>{busy?'Please wait…':mode==='login'?'Sign in':mode==='signup'?'Create account':mode==='forgot'?'Send reset link':mode==='verify'?'Resend verification':'Save password'}</button>
 {['login','signup'].includes(mode)&&<><div className="auth-bottom">or</div><button type="button" className="btn secondary block" disabled={busy} onClick={googleSignIn}>Continue with Google</button></>}
 <div className="auth-bottom">{mode==='login'?<>New to Orbit? <a href="/signup">Create account</a><br/><a href="/forgot-password">Forgot password?</a></>:mode==='signup'?<>Already registered? <a href="/login">Sign in</a></>:<a href="/login">Return to sign in</a>}</div></form>
}
