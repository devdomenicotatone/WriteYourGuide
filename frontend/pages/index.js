// index.js

import { useState } from 'react';

export default function Home() {
  const [query, setQuery] = useState("");
  const [risultati, setRisultati] = useState([]);
  const [immagini, setImmagini] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Inserisci qui l'indirizzo del tuo backend
  const backendUrl = "https://metawrite.onrender.com";

  const handleGenerateArticle = async () => {
    setLoading(true);
    setError(null);
    setRisultati([]);
    setImmagini([]);

    try {
      const res = await fetch(`${backendUrl}/generate_article`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ query })
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Errore nella generazione dell'articolo");
      }

      const data = await res.json();
      setRisultati(data.risultati || []);
      setImmagini(data.immagini || []);
    } catch (err) {
      setError(err.message || "Errore sconosciuto");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{padding: "20px", fontFamily: "Arial, sans-serif"}}>
      <h1>MetaWrite - Generatore di Articoli</h1>
      <p>Inserisci una città o un luogo e genera un testo basato sulle guide di GetYourGuide.</p>

      <div style={{marginBottom: "20px"}}>
        <input 
          type="text" 
          value={query} 
          onChange={(e) => setQuery(e.target.value)} 
          placeholder="Ad es. 'Lanzarote'" 
          style={{padding: "10px", width: "300px"}}
        />
        <button 
          onClick={handleGenerateArticle} 
          style={{padding: "10px 20px", marginLeft: "10px"}}
        >
          Genera Articolo
        </button>
      </div>

      {loading && <p>Generazione in corso...</p>}
      {error && <p style={{color: "red"}}>Errore: {error}</p>}

      {risultati.length > 0 && (
        <div style={{border: "1px solid #ccc", padding: "20px", marginBottom: "20px"}}>
          <h2>Contenuti Generati</h2>
          {risultati.map((item, index) => (
            <div key={index} style={{marginBottom: "20px"}}>
              <h2>{item.titolo}</h2>
              <p>{item.contenuto}</p>
            </div>
          ))}
        </div>
      )}

      {immagini.length > 0 && (
        <div style={{border: "1px solid #ccc", padding: "20px"}}>
          <h2>Immagini Estratte</h2>
          <div style={{display: 'flex', flexWrap: 'wrap', gap: '10px'}}>
            {immagini.map((img, idx) => (
              <div key={idx}>
                <img src={img} alt="Immagine Tour" style={{maxWidth: "200px", height: "auto"}} />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
