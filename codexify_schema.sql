--
-- PostgreSQL database dump
--

\restrict aHM0CzSKJ1nZ8TVoyhtUSR9n3aeB1tv6rDk60Z1XysPsSGpW6LcryY6es6awrfs

-- Dumped from database version 15.15 (Debian 15.15-1.pgdg13+1)
-- Dumped by pg_dump version 15.15 (Debian 15.15-1.pgdg13+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


--
-- Name: audit_log; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_log (
    id bigint NOT NULL,
    event text NOT NULL,
    entity text NOT NULL,
    entity_id text NOT NULL,
    user_id text NOT NULL,
    "timestamp" timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: audit_log_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.audit_log_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: audit_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.audit_log_id_seq OWNED BY public.audit_log.id;


--
-- Name: chat_messages; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.chat_messages (
    id bigint NOT NULL,
    thread_id integer NOT NULL,
    role character varying(32) NOT NULL,
    content text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: chat_messages_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.chat_messages_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: chat_messages_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.chat_messages_id_seq OWNED BY public.chat_messages.id;


--
-- Name: chat_threads; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.chat_threads (
    id integer NOT NULL,
    user_id character varying(255) NOT NULL,
    title character varying(512) NOT NULL,
    summary text DEFAULT ''::text NOT NULL,
    project_id integer,
    parent_id integer,
    archived_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    is_diary boolean DEFAULT false NOT NULL,
    exclude_from_identity boolean DEFAULT false NOT NULL,
    metadata jsonb
);


--
-- Name: chat_threads_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.chat_threads_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: chat_threads_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.chat_threads_id_seq OWNED BY public.chat_threads.id;


--
-- Name: connector_configs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.connector_configs (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    type character varying(64) NOT NULL,
    config jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    schedule character varying(255)
);


--
-- Name: connector_configs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.connector_configs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: connector_configs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.connector_configs_id_seq OWNED BY public.connector_configs.id;


--
-- Name: connector_runs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.connector_runs (
    id bigint NOT NULL,
    config_id integer NOT NULL,
    status character varying(32) NOT NULL,
    started_at timestamp with time zone NOT NULL,
    finished_at timestamp with time zone,
    error text,
    document_count integer DEFAULT 0 NOT NULL
);


--
-- Name: connector_runs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.connector_runs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: connector_runs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.connector_runs_id_seq OWNED BY public.connector_runs.id;


--
-- Name: events_outbox; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.events_outbox (
    id bigint NOT NULL,
    topic character varying(128),
    payload jsonb,
    status character varying(32) DEFAULT 'pending'::character varying NOT NULL,
    tenant_id character varying(64) DEFAULT 'default'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: events_outbox_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.events_outbox_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: events_outbox_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.events_outbox_id_seq OWNED BY public.events_outbox.id;


--
-- Name: generated_documents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.generated_documents (
    id character varying(36) NOT NULL,
    project_id integer,
    thread_id integer,
    user_id character varying(255),
    title text NOT NULL,
    content text NOT NULL,
    format character varying(32) NOT NULL,
    model character varying(255) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    CONSTRAINT generated_documents_format_check CHECK (((format)::text = ANY ((ARRAY['txt'::character varying, 'md'::character varying, 'docx'::character varying, 'pdf'::character varying, 'html'::character varying, 'json'::character varying])::text[])))
);


--
-- Name: generated_images; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.generated_images (
    id character varying(36) NOT NULL,
    project_id integer NOT NULL,
    thread_id integer NOT NULL,
    user_id character varying(255) NOT NULL,
    src_url text NOT NULL,
    prompt text NOT NULL,
    model character varying(255) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone
);


--
-- Name: imprints; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.imprints (
    id integer NOT NULL,
    user_id character varying(255) NOT NULL,
    project_id integer,
    guardian_name text,
    preferred_name text,
    style text,
    grammar_prefs jsonb DEFAULT '{}'::jsonb NOT NULL,
    metrics jsonb DEFAULT '{}'::jsonb NOT NULL,
    heat_score double precision,
    status character varying(32) DEFAULT 'draft'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT imprints_status_check CHECK (((status)::text = ANY ((ARRAY['draft'::character varying, 'active'::character varying, 'superseded'::character varying])::text[])))
);


--
-- Name: imprints_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.imprints_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: imprints_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.imprints_id_seq OWNED BY public.imprints.id;


--
-- Name: memory_entries; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.memory_entries (
    id bigint NOT NULL,
    user_id character varying(255),
    silo character varying(64) NOT NULL,
    content text,
    tags text,
    pinned boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT memory_entries_silo_check CHECK (((silo)::text = ANY ((ARRAY['ephemeral'::character varying, 'midterm'::character varying, 'longterm'::character varying])::text[])))
);


--
-- Name: memory_entries_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.memory_entries_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: memory_entries_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.memory_entries_id_seq OWNED BY public.memory_entries.id;


--
-- Name: messages; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.messages (
    id bigint NOT NULL,
    thread_id character varying(255) NOT NULL,
    role character varying(32) NOT NULL,
    content text NOT NULL,
    "timestamp" timestamp with time zone DEFAULT now() NOT NULL,
    tenant_id character varying(64) DEFAULT 'default'::character varying NOT NULL
);


--
-- Name: messages_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.messages_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: messages_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.messages_id_seq OWNED BY public.messages.id;


--
-- Name: personas; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.personas (
    id integer NOT NULL,
    user_id character varying(255) NOT NULL,
    project_id integer,
    body text NOT NULL,
    source character varying(64) DEFAULT 'user'::character varying NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: personas_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.personas_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: personas_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.personas_id_seq OWNED BY public.personas.id;


--
-- Name: projects; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.projects (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    icon character varying(16),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: projects_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.projects_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: projects_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.projects_id_seq OWNED BY public.projects.id;


--
-- Name: raw_documents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.raw_documents (
    id bigint NOT NULL,
    config_id integer NOT NULL,
    external_id character varying(512) NOT NULL,
    payload jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: raw_documents_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.raw_documents_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: raw_documents_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.raw_documents_id_seq OWNED BY public.raw_documents.id;


--
-- Name: sync_jobs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sync_jobs (
    id integer NOT NULL,
    connector_id character varying(255) NOT NULL,
    status character varying(32) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    started_at timestamp with time zone,
    finished_at timestamp with time zone,
    attempts integer DEFAULT 0 NOT NULL,
    last_error text,
    metadata jsonb
);


--
-- Name: sync_jobs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.sync_jobs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: sync_jobs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.sync_jobs_id_seq OWNED BY public.sync_jobs.id;


--
-- Name: system_doc_links; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.system_doc_links (
    id integer NOT NULL,
    user_id character varying(255) NOT NULL,
    project_id integer,
    system_doc_id integer NOT NULL,
    is_enabled boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: system_doc_links_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.system_doc_links_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: system_doc_links_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.system_doc_links_id_seq OWNED BY public.system_doc_links.id;


--
-- Name: system_docs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.system_docs (
    id integer NOT NULL,
    scope character varying(16) NOT NULL,
    owner_user_id character varying(255),
    project_id integer,
    slug character varying(255) NOT NULL,
    title character varying(255) NOT NULL,
    content text NOT NULL,
    is_enabled boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT system_docs_scope_check CHECK (((scope)::text = ANY ((ARRAY['global'::character varying, 'project'::character varying, 'user'::character varying])::text[])))
);


--
-- Name: system_docs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.system_docs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: system_docs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.system_docs_id_seq OWNED BY public.system_docs.id;


--
-- Name: tts_outputs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tts_outputs (
    id bigint NOT NULL,
    project_id integer,
    thread_id integer,
    user_id character varying(255),
    text text NOT NULL,
    voice character varying(128),
    provider character varying(128),
    model character varying(255),
    src_url text,
    duration_seconds integer,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: tts_outputs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.tts_outputs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: tts_outputs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.tts_outputs_id_seq OWNED BY public.tts_outputs.id;


--
-- Name: uploaded_documents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.uploaded_documents (
    id character varying(36) NOT NULL,
    project_id integer,
    thread_id integer,
    user_id character varying(255),
    filename character varying(512) NOT NULL,
    filesize bigint NOT NULL,
    mime_type character varying(128) NOT NULL,
    src_url text NOT NULL,
    parsed_text text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone
);


--
-- Name: uploaded_images; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.uploaded_images (
    id character varying(36) NOT NULL,
    project_id integer NOT NULL,
    thread_id integer NOT NULL,
    user_id character varying(255) NOT NULL,
    src_url text NOT NULL,
    filename character varying(512) NOT NULL,
    filesize bigint NOT NULL,
    mime_type character varying(128) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone
);


--
-- Name: audit_log id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_log ALTER COLUMN id SET DEFAULT nextval('public.audit_log_id_seq'::regclass);


--
-- Name: chat_messages id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_messages ALTER COLUMN id SET DEFAULT nextval('public.chat_messages_id_seq'::regclass);


--
-- Name: chat_threads id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_threads ALTER COLUMN id SET DEFAULT nextval('public.chat_threads_id_seq'::regclass);


--
-- Name: connector_configs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.connector_configs ALTER COLUMN id SET DEFAULT nextval('public.connector_configs_id_seq'::regclass);


--
-- Name: connector_runs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.connector_runs ALTER COLUMN id SET DEFAULT nextval('public.connector_runs_id_seq'::regclass);


--
-- Name: events_outbox id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.events_outbox ALTER COLUMN id SET DEFAULT nextval('public.events_outbox_id_seq'::regclass);


--
-- Name: imprints id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.imprints ALTER COLUMN id SET DEFAULT nextval('public.imprints_id_seq'::regclass);


--
-- Name: memory_entries id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.memory_entries ALTER COLUMN id SET DEFAULT nextval('public.memory_entries_id_seq'::regclass);


--
-- Name: messages id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.messages ALTER COLUMN id SET DEFAULT nextval('public.messages_id_seq'::regclass);


--
-- Name: personas id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.personas ALTER COLUMN id SET DEFAULT nextval('public.personas_id_seq'::regclass);


--
-- Name: projects id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.projects ALTER COLUMN id SET DEFAULT nextval('public.projects_id_seq'::regclass);


--
-- Name: raw_documents id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.raw_documents ALTER COLUMN id SET DEFAULT nextval('public.raw_documents_id_seq'::regclass);


--
-- Name: sync_jobs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sync_jobs ALTER COLUMN id SET DEFAULT nextval('public.sync_jobs_id_seq'::regclass);


--
-- Name: system_doc_links id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.system_doc_links ALTER COLUMN id SET DEFAULT nextval('public.system_doc_links_id_seq'::regclass);


--
-- Name: system_docs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.system_docs ALTER COLUMN id SET DEFAULT nextval('public.system_docs_id_seq'::regclass);


--
-- Name: tts_outputs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tts_outputs ALTER COLUMN id SET DEFAULT nextval('public.tts_outputs_id_seq'::regclass);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: audit_log audit_log_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_log
    ADD CONSTRAINT audit_log_pkey PRIMARY KEY (id);


--
-- Name: chat_messages chat_messages_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_messages
    ADD CONSTRAINT chat_messages_pkey PRIMARY KEY (id);


--
-- Name: chat_threads chat_threads_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_threads
    ADD CONSTRAINT chat_threads_pkey PRIMARY KEY (id);


--
-- Name: connector_configs connector_configs_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.connector_configs
    ADD CONSTRAINT connector_configs_name_key UNIQUE (name);


--
-- Name: connector_configs connector_configs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.connector_configs
    ADD CONSTRAINT connector_configs_pkey PRIMARY KEY (id);


--
-- Name: connector_runs connector_runs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.connector_runs
    ADD CONSTRAINT connector_runs_pkey PRIMARY KEY (id);


--
-- Name: events_outbox events_outbox_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.events_outbox
    ADD CONSTRAINT events_outbox_pkey PRIMARY KEY (id);


--
-- Name: generated_documents generated_documents_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.generated_documents
    ADD CONSTRAINT generated_documents_pkey PRIMARY KEY (id);


--
-- Name: generated_images generated_images_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.generated_images
    ADD CONSTRAINT generated_images_pkey PRIMARY KEY (id);


--
-- Name: imprints imprints_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.imprints
    ADD CONSTRAINT imprints_pkey PRIMARY KEY (id);


--
-- Name: memory_entries memory_entries_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.memory_entries
    ADD CONSTRAINT memory_entries_pkey PRIMARY KEY (id);


--
-- Name: messages messages_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_pkey PRIMARY KEY (id);


--
-- Name: personas personas_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.personas
    ADD CONSTRAINT personas_pkey PRIMARY KEY (id);


--
-- Name: projects projects_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT projects_name_key UNIQUE (name);


--
-- Name: projects projects_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT projects_pkey PRIMARY KEY (id);


--
-- Name: raw_documents raw_documents_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.raw_documents
    ADD CONSTRAINT raw_documents_pkey PRIMARY KEY (id);


--
-- Name: sync_jobs sync_jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sync_jobs
    ADD CONSTRAINT sync_jobs_pkey PRIMARY KEY (id);


--
-- Name: system_doc_links system_doc_links_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.system_doc_links
    ADD CONSTRAINT system_doc_links_pkey PRIMARY KEY (id);


--
-- Name: system_docs system_docs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.system_docs
    ADD CONSTRAINT system_docs_pkey PRIMARY KEY (id);


--
-- Name: tts_outputs tts_outputs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tts_outputs
    ADD CONSTRAINT tts_outputs_pkey PRIMARY KEY (id);


--
-- Name: uploaded_documents uploaded_documents_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.uploaded_documents
    ADD CONSTRAINT uploaded_documents_pkey PRIMARY KEY (id);


--
-- Name: uploaded_images uploaded_images_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.uploaded_images
    ADD CONSTRAINT uploaded_images_pkey PRIMARY KEY (id);


--
-- Name: system_doc_links uq_system_doc_links_attachment; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.system_doc_links
    ADD CONSTRAINT uq_system_doc_links_attachment UNIQUE (user_id, project_id, system_doc_id);


--
-- Name: system_docs uq_system_docs_scope_owner_project_slug; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.system_docs
    ADD CONSTRAINT uq_system_docs_scope_owner_project_slug UNIQUE (scope, owner_user_id, project_id, slug);


--
-- Name: ix_audit_log_entity; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_log_entity ON public.audit_log USING btree (entity, entity_id);


--
-- Name: ix_audit_log_timestamp; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_log_timestamp ON public.audit_log USING btree ("timestamp" DESC);


--
-- Name: ix_chat_messages_thread_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_chat_messages_thread_created ON public.chat_messages USING btree (thread_id, created_at);


--
-- Name: ix_chat_messages_thread_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_chat_messages_thread_id ON public.chat_messages USING btree (thread_id);


--
-- Name: ix_chat_threads_parent_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_chat_threads_parent_id ON public.chat_threads USING btree (parent_id);


--
-- Name: ix_chat_threads_project_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_chat_threads_project_id ON public.chat_threads USING btree (project_id);


--
-- Name: ix_chat_threads_updated; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_chat_threads_updated ON public.chat_threads USING btree (updated_at DESC);


--
-- Name: ix_chat_threads_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_chat_threads_user_id ON public.chat_threads USING btree (user_id);


--
-- Name: ix_connector_runs_config_started; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_connector_runs_config_started ON public.connector_runs USING btree (config_id, started_at DESC);


--
-- Name: ix_events_outbox_status_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_events_outbox_status_created ON public.events_outbox USING btree (status, created_at);


--
-- Name: ix_events_outbox_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_events_outbox_tenant_id ON public.events_outbox USING btree (tenant_id);


--
-- Name: ix_generated_documents_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_generated_documents_created ON public.generated_documents USING btree (created_at DESC);


--
-- Name: ix_generated_documents_format; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_generated_documents_format ON public.generated_documents USING btree (format);


--
-- Name: ix_generated_documents_project; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_generated_documents_project ON public.generated_documents USING btree (project_id);


--
-- Name: ix_generated_documents_thread; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_generated_documents_thread ON public.generated_documents USING btree (thread_id);


--
-- Name: ix_generated_images_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_generated_images_created ON public.generated_images USING btree (created_at DESC);


--
-- Name: ix_generated_images_project; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_generated_images_project ON public.generated_images USING btree (project_id);


--
-- Name: ix_generated_images_thread; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_generated_images_thread ON public.generated_images USING btree (thread_id);


--
-- Name: ix_generated_images_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_generated_images_user ON public.generated_images USING btree (user_id);


--
-- Name: ix_imprints_active_unique; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_imprints_active_unique ON public.imprints USING btree (user_id, project_id) WHERE ((status)::text = 'active'::text);


--
-- Name: ix_memory_entries_silo; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_memory_entries_silo ON public.memory_entries USING btree (silo);


--
-- Name: ix_memory_entries_silo_updated; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_memory_entries_silo_updated ON public.memory_entries USING btree (silo, updated_at);


--
-- Name: ix_memory_entries_user_silo; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_memory_entries_user_silo ON public.memory_entries USING btree (user_id, silo);


--
-- Name: ix_messages_thread_id_timestamp; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_messages_thread_id_timestamp ON public.messages USING btree (thread_id, "timestamp");


--
-- Name: ix_personas_active_unique; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_personas_active_unique ON public.personas USING btree (user_id, project_id) WHERE is_active;


--
-- Name: ix_raw_documents_config_external; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_raw_documents_config_external ON public.raw_documents USING btree (config_id, external_id);


--
-- Name: ix_sync_jobs_connector_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sync_jobs_connector_created ON public.sync_jobs USING btree (connector_id, created_at);


--
-- Name: ix_tts_outputs_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tts_outputs_created ON public.tts_outputs USING btree (created_at DESC);


--
-- Name: ix_tts_outputs_project; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tts_outputs_project ON public.tts_outputs USING btree (project_id);


--
-- Name: ix_tts_outputs_provider; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tts_outputs_provider ON public.tts_outputs USING btree (provider);


--
-- Name: ix_tts_outputs_thread; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tts_outputs_thread ON public.tts_outputs USING btree (thread_id);


--
-- Name: ix_uploaded_documents_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_uploaded_documents_created ON public.uploaded_documents USING btree (created_at DESC);


--
-- Name: ix_uploaded_documents_mime; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_uploaded_documents_mime ON public.uploaded_documents USING btree (mime_type);


--
-- Name: ix_uploaded_documents_project; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_uploaded_documents_project ON public.uploaded_documents USING btree (project_id);


--
-- Name: ix_uploaded_documents_thread; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_uploaded_documents_thread ON public.uploaded_documents USING btree (thread_id);


--
-- Name: ix_uploaded_images_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_uploaded_images_created ON public.uploaded_images USING btree (created_at DESC);


--
-- Name: ix_uploaded_images_mime; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_uploaded_images_mime ON public.uploaded_images USING btree (mime_type);


--
-- Name: ix_uploaded_images_project; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_uploaded_images_project ON public.uploaded_images USING btree (project_id);


--
-- Name: ix_uploaded_images_thread; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_uploaded_images_thread ON public.uploaded_images USING btree (thread_id);


--
-- Name: ix_uploaded_images_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_uploaded_images_user ON public.uploaded_images USING btree (user_id);


--
-- Name: chat_messages chat_messages_thread_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_messages
    ADD CONSTRAINT chat_messages_thread_id_fkey FOREIGN KEY (thread_id) REFERENCES public.chat_threads(id) ON DELETE CASCADE;


--
-- Name: chat_threads chat_threads_parent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_threads
    ADD CONSTRAINT chat_threads_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES public.chat_threads(id);


--
-- Name: chat_threads chat_threads_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_threads
    ADD CONSTRAINT chat_threads_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);


--
-- Name: connector_runs connector_runs_config_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.connector_runs
    ADD CONSTRAINT connector_runs_config_id_fkey FOREIGN KEY (config_id) REFERENCES public.connector_configs(id) ON DELETE CASCADE;


--
-- Name: generated_documents generated_documents_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.generated_documents
    ADD CONSTRAINT generated_documents_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON DELETE CASCADE;


--
-- Name: generated_documents generated_documents_thread_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.generated_documents
    ADD CONSTRAINT generated_documents_thread_id_fkey FOREIGN KEY (thread_id) REFERENCES public.chat_threads(id) ON DELETE CASCADE;


--
-- Name: generated_images generated_images_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.generated_images
    ADD CONSTRAINT generated_images_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON DELETE CASCADE;


--
-- Name: generated_images generated_images_thread_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.generated_images
    ADD CONSTRAINT generated_images_thread_id_fkey FOREIGN KEY (thread_id) REFERENCES public.chat_threads(id) ON DELETE CASCADE;


--
-- Name: raw_documents raw_documents_config_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.raw_documents
    ADD CONSTRAINT raw_documents_config_id_fkey FOREIGN KEY (config_id) REFERENCES public.connector_configs(id) ON DELETE CASCADE;


--
-- Name: system_doc_links system_doc_links_system_doc_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.system_doc_links
    ADD CONSTRAINT system_doc_links_system_doc_id_fkey FOREIGN KEY (system_doc_id) REFERENCES public.system_docs(id) ON DELETE CASCADE;


--
-- Name: tts_outputs tts_outputs_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tts_outputs
    ADD CONSTRAINT tts_outputs_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON DELETE CASCADE;


--
-- Name: tts_outputs tts_outputs_thread_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tts_outputs
    ADD CONSTRAINT tts_outputs_thread_id_fkey FOREIGN KEY (thread_id) REFERENCES public.chat_threads(id) ON DELETE CASCADE;


--
-- Name: uploaded_documents uploaded_documents_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.uploaded_documents
    ADD CONSTRAINT uploaded_documents_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON DELETE CASCADE;


--
-- Name: uploaded_documents uploaded_documents_thread_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.uploaded_documents
    ADD CONSTRAINT uploaded_documents_thread_id_fkey FOREIGN KEY (thread_id) REFERENCES public.chat_threads(id) ON DELETE CASCADE;


--
-- Name: uploaded_images uploaded_images_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.uploaded_images
    ADD CONSTRAINT uploaded_images_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON DELETE CASCADE;


--
-- Name: uploaded_images uploaded_images_thread_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.uploaded_images
    ADD CONSTRAINT uploaded_images_thread_id_fkey FOREIGN KEY (thread_id) REFERENCES public.chat_threads(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict aHM0CzSKJ1nZ8TVoyhtUSR9n3aeB1tv6rDk60Z1XysPsSGpW6LcryY6es6awrfs
