/*
We create the dapr_web table to store web content
and the lastupdate column to track when the content was last updated.
This table is used by the Dapr injection agent to fetch and process web content.
The lastupdate column is used to filter out content that has not been updated recently,
ensuring that the agent only processes fresh content.
*/

    CREATE TABLE IF NOT EXISTS dapr_web (
      id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
      url TEXT,
      text TEXT
    );

    ALTER TABLE dapr_web ADD COLUMN lastupdate DATE;
    -- update dapr_web  set lastupdate =  CURRENT_DATE - INTERVAL '8 days';
    insert into dapr_web (url, text, lastupdate) values ('https://example.com', 'Example content', CURRENT_DATE - INTERVAL '90 days');