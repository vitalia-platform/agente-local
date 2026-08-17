import { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import { GlassPanel } from '../components/GlassPanel';
import styles from './QueueInspector.module.css';

interface QueueInfo {
  name: string;
  length: number;
}

export function QueueInspector() {
  const [queues, setQueues] = useState<QueueInfo[]>([]);
  const [selectedQueue, setSelectedQueue] = useState<string | null>(null);
  const [messages, setMessages] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMessages, setLoadingMessages] = useState(false);

  useEffect(() => {
    const fetchQueues = async () => {
      try {
        const { data } = await apiClient.get('/queues');
        setQueues(data.queues || []);
      } catch (err) {
        console.error('Failed to fetch queues', err);
      } finally {
        setLoading(false);
      }
    };
    fetchQueues();
  }, []);

  const selectQueue = async (name: string) => {
    setSelectedQueue(name);
    setLoadingMessages(true);
    try {
      const { data } = await apiClient.get(`/queues/${name}`);
      setMessages(data.messages || []);
    } catch (err) {
      console.error('Failed to fetch messages', err);
      setMessages([]);
    } finally {
      setLoadingMessages(false);
    }
  };

  return (
    <div className={styles.container}>
      <h1 className={styles.title}>Queue Inspector</h1>
      <p className={styles.subtitle}>Inspect Redis Streams and Message Payloads</p>

      <div className={styles.layout}>
        <GlassPanel className={styles.sidebar}>
          <h3>Active Queues</h3>
          {loading ? (
            <p>Loading...</p>
          ) : queues.length === 0 ? (
            <p className={styles.empty}>No active queues found.</p>
          ) : (
            <ul className={styles.queueList}>
              {queues.map(q => (
                <li 
                  key={q.name} 
                  className={selectedQueue === q.name ? styles.activeQueue : ''}
                  onClick={() => selectQueue(q.name)}
                >
                  <span className={styles.qName}>{q.name}</span>
                  <span className={styles.qLength}>{q.length}</span>
                </li>
              ))}
            </ul>
          )}
        </GlassPanel>

        <GlassPanel className={styles.mainArea}>
          {selectedQueue ? (
            <>
              <div className={styles.mainHeader}>
                <h3>Messages: {selectedQueue}</h3>
              </div>
              
              {loadingMessages ? (
                <p>Loading messages...</p>
              ) : messages.length === 0 ? (
                <p className={styles.empty}>No messages in this queue.</p>
              ) : (
                <div className={styles.messageList}>
                  {messages.map((msg) => (
                    <div key={msg.id} className={styles.messageItem}>
                      <div className={styles.msgHeader}>ID: {msg.id}</div>
                      <pre className={styles.jsonViewer}>
                        {JSON.stringify(msg.payload, null, 2)}
                      </pre>
                    </div>
                  ))}
                </div>
              )}
            </>
          ) : (
            <div className={styles.placeholder}>
              <p>Select a queue from the sidebar to inspect messages.</p>
            </div>
          )}
        </GlassPanel>
      </div>
    </div>
  );
}
