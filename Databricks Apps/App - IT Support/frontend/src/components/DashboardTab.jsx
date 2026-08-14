import React from 'react';

const DASHBOARD_URL =
  'https://fevm-cosin-aws-serverless.cloud.databricks.com/embed/dashboardsv3/01f124531fa91f9b9039abc401106002';

export default function DashboardTab() {
  return (
    <div className="h-full w-full p-4">
      <iframe
        src={DASHBOARD_URL}
        title="AIBI Dashboard - Support IT"
        className="w-full h-full rounded-lg border border-db-primary/30"
        style={{ background: '#fff' }}
        allow="fullscreen"
      />
    </div>
  );
}
