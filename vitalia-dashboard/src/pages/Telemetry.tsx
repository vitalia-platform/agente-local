import { useWebSocket } from '../hooks/useWebSocket';
import { GlassPanel } from '../components/GlassPanel';
import styles from './Telemetry.module.css';

export function Telemetry() {
  const { events, isConnected } = useWebSocket('/ws/events');

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1 className={styles.title}>Telemetry HUD</h1>
        <div className={`${styles.statusBadge} ${isConnected ? styles.connected : styles.disconnected}`}>
          {isConnected ? 'LIVE' : 'DISCONNECTED'}
        </div>
      </header>
      
      <div className={styles.grid}>
        <GlassPanel className={styles.panel}>
          <h2>System Events Stream</h2>
          <div className={styles.eventLog}>
            {events.length === 0 ? (
              <p className={styles.empty}>Waiting for events...</p>
            ) : (
              events.map((evt, idx) => (
                <div key={idx} className={styles.eventItem}>
                  <span className={styles.timestamp}>
                    {new Date().toLocaleTimeString()}
                  </span>
                  <span className={styles.eventName}>{evt.event}</span>
                  <pre className={styles.eventPayload}>
                    {JSON.stringify(evt, null, 2)}
                  </pre>
                </div>
              ))
            )}
          </div>
        </GlassPanel>

        <div className={styles.sideGrid}>
          <GlassPanel className={styles.panel}>
            <h2>GPU Status (Placeholder)</h2>
            <div className={styles.gaugeContainer}>
              <div className={styles.gauge}>
                <div className={styles.gaugeFill} style={{ width: '45%' }}></div>
              </div>
              <p>45% VRAM Used</p>
            </div>
          </GlassPanel>

          <GlassPanel className={styles.panel}>
            <h2>Active Streams</h2>
            <p className={styles.metric}>3 Streams Processing</p>
          </GlassPanel>
        </div>
      </div>
    </div>
  );
}
