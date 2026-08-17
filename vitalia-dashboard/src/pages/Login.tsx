import { useState, useContext } from 'react';
import { GlassPanel } from '../components/GlassPanel';
import { NeonButton } from '../components/NeonButton';
import { AuthContext } from '../context/AuthContext';
import styles from './Login.module.css';

export function Login() {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useContext(AuthContext);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const formData = new URLSearchParams();
      formData.append('username', 'admin');
      formData.append('password', password);

      const res = await fetch('http://localhost:8000/api/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: formData.toString(),
      });

      if (!res.ok) {
        throw new Error('Senha mestra incorreta');
      }

      const data = await res.json();
      login(data.access_token);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.container}>
      <GlassPanel className={styles.loginPanel}>
        <h1 className={styles.title}>Vitalia Control Plane</h1>
        <p className={styles.subtitle}>Enter master password to continue</p>
        
        <form onSubmit={handleSubmit} className={styles.form}>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className={styles.input}
            placeholder="Master Password"
            autoFocus
          />
          {error && <p className={styles.error}>{error}</p>}
          <NeonButton type="submit" disabled={loading} style={{ width: '100%' }}>
            {loading ? 'Authenticating...' : 'Enter System'}
          </NeonButton>
        </form>
      </GlassPanel>
    </div>
  );
}
