import React from 'react';

const GENIE_SPACE_ID = '01f124528653102d8b5ea6443c331153';
const GENIE_EMBED_URL =
  `https://fevm-cosin-aws-serverless.cloud.databricks.com/embed/genie/rooms/${GENIE_SPACE_ID}?o=7474659847183384`;

export default function GenieTab() {
  return (
    <div className="h-full w-full p-4">
      <iframe
        src={GENIE_EMBED_URL}
        title="Genie - Sala Chamados IT"
        className="w-full h-full rounded-lg border border-db-primary/30"
        style={{ background: '#fff' }}
        frameBorder="0"
        allow="clipboard-write"
      />
    </div>
  );
}
