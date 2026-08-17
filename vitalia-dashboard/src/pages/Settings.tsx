import { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import { GlassPanel } from '../components/GlassPanel';
import { NeonButton } from '../components/NeonButton';
import styles from './Settings.module.css';

export function Settings() {
  const [settings, setSettings] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [benchmarkResult, setBenchmarkResult] = useState<any>(null);

  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const { data } = await apiClient.get('/settings');
        setSettings(data);
      } catch (err) {
        console.error('Failed to fetch settings', err);
      } finally {
        setLoading(false);
      }
    };
    fetchSettings();
  }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      await apiClient.post('/settings', { settings });
      alert('Settings saved successfully');
    } catch (err) {
      alert('Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  const handleChange = (key: string, value: string) => {
    setSettings(prev => ({ ...prev, [key]: value }));
  };

  const runBenchmark = async () => {
    try {
      setBenchmarkResult({ status: 'running...' });
      const { data } = await apiClient.post('/benchmark', {
        endpoint_url: settings['NO1_LOCAL_OLLAMA_URL'] || 'http://localhost:11434/api/generate',
        model_name: 'llama3:latest' // Placeholder default
      });
      setBenchmarkResult(data);
    } catch (err: any) {
      setBenchmarkResult({ error: err.message });
    }
  };

  return (
    <div className={styles.container}>
      <h1 className={styles.title}>System Settings</h1>
      
      <div className={styles.grid}>
        <GlassPanel className={styles.panel}>
          <h2>Environment Configuration</h2>
          {loading ? (
            <p>Loading...</p>
          ) : (
            <div className={styles.formGroup}>
              {Object.entries(settings).map(([key, val]) => (
                <div key={key} className={styles.inputRow}>
                  <label>{key}</label>
                  <input 
                    type="text" 
                    value={val} 
                    onChange={e => handleChange(key, e.target.value)}
                    className={styles.input}
                  />
                </div>
              ))}
              <NeonButton onClick={handleSave} disabled={saving} style={{ marginTop: '1rem' }}>
                {saving ? 'Saving...' : 'Save Settings'}
              </NeonButton>
            </div>
          )}
        </GlassPanel>

        <GlassPanel className={styles.panel}>
          <h2>Benchmark Tool</h2>
          <p className={styles.description}>Test the configured local Ollama endpoint performance.</p>
          <NeonButton onClick={runBenchmark} variant="primary">
            Run Benchmark
          </NeonButton>
          
          {benchmarkResult && (
            <div className={styles.resultBox}>
              <pre>{JSON.stringify(benchmarkResult, null, 2)}</pre>
            </div>
          )}
        </GlassPanel>
      </div>
    </div>
  );
}
