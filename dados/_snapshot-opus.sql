--
-- PostgreSQL database dump
--

\restrict XCri1puZQTC9iFmWtnT6BKT7orge8uehCdriEUravCx6gaMcBlkEsAVza0InGUy

-- Dumped from database version 16.15
-- Dumped by pg_dump version 16.15

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

ALTER TABLE IF EXISTS ONLY public.reviews DROP CONSTRAINT IF EXISTS reviews_user_id_fkey;
ALTER TABLE IF EXISTS ONLY public.reviews DROP CONSTRAINT IF EXISTS reviews_product_id_fkey;
ALTER TABLE IF EXISTS ONLY public.products DROP CONSTRAINT IF EXISTS products_category_id_fkey;
ALTER TABLE IF EXISTS ONLY public.password_reset_tokens DROP CONSTRAINT IF EXISTS password_reset_tokens_user_id_fkey;
ALTER TABLE IF EXISTS ONLY public.orders DROP CONSTRAINT IF EXISTS orders_user_id_fkey;
ALTER TABLE IF EXISTS ONLY public.order_items DROP CONSTRAINT IF EXISTS order_items_product_id_fkey;
ALTER TABLE IF EXISTS ONLY public.order_items DROP CONSTRAINT IF EXISTS order_items_order_id_fkey;
ALTER TABLE IF EXISTS ONLY public.cart_items DROP CONSTRAINT IF EXISTS cart_items_user_id_fkey;
ALTER TABLE IF EXISTS ONLY public.cart_items DROP CONSTRAINT IF EXISTS cart_items_product_id_fkey;
DROP INDEX IF EXISTS public.reviews_product_idx;
DROP INDEX IF EXISTS public.products_name_idx;
DROP INDEX IF EXISTS public.products_category_idx;
DROP INDEX IF EXISTS public.password_reset_tokens_user_idx;
DROP INDEX IF EXISTS public.orders_user_idx;
DROP INDEX IF EXISTS public.order_items_order_idx;
DROP INDEX IF EXISTS public.cart_items_user_idx;
ALTER TABLE IF EXISTS ONLY public.users DROP CONSTRAINT IF EXISTS users_pkey;
ALTER TABLE IF EXISTS ONLY public.users DROP CONSTRAINT IF EXISTS users_email_key;
ALTER TABLE IF EXISTS ONLY public.schema_migrations DROP CONSTRAINT IF EXISTS schema_migrations_pkey;
ALTER TABLE IF EXISTS ONLY public.reviews DROP CONSTRAINT IF EXISTS reviews_product_id_user_id_key;
ALTER TABLE IF EXISTS ONLY public.reviews DROP CONSTRAINT IF EXISTS reviews_pkey;
ALTER TABLE IF EXISTS ONLY public.products DROP CONSTRAINT IF EXISTS products_pkey;
ALTER TABLE IF EXISTS ONLY public.password_reset_tokens DROP CONSTRAINT IF EXISTS password_reset_tokens_token_hash_key;
ALTER TABLE IF EXISTS ONLY public.password_reset_tokens DROP CONSTRAINT IF EXISTS password_reset_tokens_pkey;
ALTER TABLE IF EXISTS ONLY public.orders DROP CONSTRAINT IF EXISTS orders_public_id_key;
ALTER TABLE IF EXISTS ONLY public.orders DROP CONSTRAINT IF EXISTS orders_pkey;
ALTER TABLE IF EXISTS ONLY public.order_items DROP CONSTRAINT IF EXISTS order_items_pkey;
ALTER TABLE IF EXISTS ONLY public.categories DROP CONSTRAINT IF EXISTS categories_slug_key;
ALTER TABLE IF EXISTS ONLY public.categories DROP CONSTRAINT IF EXISTS categories_pkey;
ALTER TABLE IF EXISTS ONLY public.categories DROP CONSTRAINT IF EXISTS categories_name_key;
ALTER TABLE IF EXISTS ONLY public.cart_items DROP CONSTRAINT IF EXISTS cart_items_user_id_product_id_key;
ALTER TABLE IF EXISTS ONLY public.cart_items DROP CONSTRAINT IF EXISTS cart_items_pkey;
DROP TABLE IF EXISTS public.users;
DROP TABLE IF EXISTS public.schema_migrations;
DROP TABLE IF EXISTS public.reviews;
DROP TABLE IF EXISTS public.products;
DROP TABLE IF EXISTS public.password_reset_tokens;
DROP TABLE IF EXISTS public.orders;
DROP TABLE IF EXISTS public.order_items;
DROP TABLE IF EXISTS public.categories;
DROP TABLE IF EXISTS public.cart_items;
DROP EXTENSION IF EXISTS pgcrypto;
--
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;


--
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: cart_items; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.cart_items (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    product_id uuid NOT NULL,
    quantity integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT cart_items_quantity_check CHECK ((quantity > 0))
);


ALTER TABLE public.cart_items OWNER TO postgres;

--
-- Name: categories; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.categories (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name text NOT NULL,
    slug text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.categories OWNER TO postgres;

--
-- Name: order_items; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.order_items (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    order_id uuid NOT NULL,
    product_id uuid,
    product_name text NOT NULL,
    unit_price_cents integer NOT NULL,
    quantity integer NOT NULL,
    CONSTRAINT order_items_quantity_check CHECK ((quantity > 0)),
    CONSTRAINT order_items_unit_price_cents_check CHECK ((unit_price_cents >= 0))
);


ALTER TABLE public.order_items OWNER TO postgres;

--
-- Name: orders; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.orders (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    public_id text NOT NULL,
    user_id uuid NOT NULL,
    status text DEFAULT 'pending'::text NOT NULL,
    total_cents integer NOT NULL,
    payment_intent_id text,
    payment_error text,
    ship_name text NOT NULL,
    ship_line1 text NOT NULL,
    ship_line2 text,
    ship_city text NOT NULL,
    ship_state text NOT NULL,
    ship_postal_code text NOT NULL,
    ship_country text NOT NULL,
    ship_phone text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT orders_status_check CHECK ((status = ANY (ARRAY['pending'::text, 'failed'::text, 'paid'::text]))),
    CONSTRAINT orders_total_cents_check CHECK ((total_cents >= 0))
);


ALTER TABLE public.orders OWNER TO postgres;

--
-- Name: password_reset_tokens; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.password_reset_tokens (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    token_hash text NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    used_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.password_reset_tokens OWNER TO postgres;

--
-- Name: products; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.products (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name text NOT NULL,
    description text DEFAULT ''::text NOT NULL,
    price_cents integer NOT NULL,
    stock integer DEFAULT 0 NOT NULL,
    image_url text,
    category_id uuid,
    active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT products_price_cents_check CHECK ((price_cents >= 0)),
    CONSTRAINT products_stock_check CHECK ((stock >= 0))
);


ALTER TABLE public.products OWNER TO postgres;

--
-- Name: reviews; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.reviews (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    product_id uuid NOT NULL,
    user_id uuid NOT NULL,
    rating integer NOT NULL,
    comment text DEFAULT ''::text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT reviews_rating_check CHECK (((rating >= 1) AND (rating <= 5)))
);


ALTER TABLE public.reviews OWNER TO postgres;

--
-- Name: schema_migrations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.schema_migrations (
    name text NOT NULL,
    applied_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.schema_migrations OWNER TO postgres;

--
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    email text NOT NULL,
    password_hash text NOT NULL,
    name text NOT NULL,
    role text DEFAULT 'customer'::text NOT NULL,
    address_line1 text,
    address_line2 text,
    city text,
    state text,
    postal_code text,
    country text,
    phone text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT users_role_check CHECK ((role = ANY (ARRAY['customer'::text, 'admin'::text])))
);


ALTER TABLE public.users OWNER TO postgres;

--
-- Data for Name: cart_items; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.cart_items (id, user_id, product_id, quantity, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: categories; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.categories (id, name, slug, created_at) FROM stdin;
0a0c3d20-92c5-4cde-9f55-26295e84ffbe	Electronics	electronics	2026-09-08 02:00:55.270726+00
473273f6-a6a9-4b64-80ec-c70ab69d2fe0	Books	books	2026-09-08 02:00:55.271732+00
fdfd5e31-0d0e-400a-b15c-423a7a7c8a17	Home & Kitchen	home-kitchen	2026-09-08 02:00:55.272369+00
2bc32d05-9a48-425e-9a42-5c3604ba06f0	Apparel	apparel	2026-09-08 02:00:55.272954+00
\.


--
-- Data for Name: order_items; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.order_items (id, order_id, product_id, product_name, unit_price_cents, quantity) FROM stdin;
4aa32fd9-7a3a-4d73-8b21-d8baaf01bc18	f47d8757-826c-408a-8ad1-188931452b49	962889b8-7f1b-46d9-a75d-aa2ac46c294c	Running Shoes	34900	2
d7ce23de-55de-416d-848a-c9c60bdc536e	c940cfc7-52ec-48be-a2e3-401ec5b4630d	962889b8-7f1b-46d9-a75d-aa2ac46c294c	Running Shoes	34900	2
\.


--
-- Data for Name: orders; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.orders (id, public_id, user_id, status, total_cents, payment_intent_id, payment_error, ship_name, ship_line1, ship_line2, ship_city, ship_state, ship_postal_code, ship_country, ship_phone, created_at, updated_at) FROM stdin;
f47d8757-826c-408a-8ad1-188931452b49	ORD-WJvtaCkyEfImgnp-nhErEA	bc1f742d-c169-4c82-9d6e-514aceee69b1	paid	69800	pi_3UDELJRG5ULykWvo1m4R2TYO	\N	Usuario Comum	Rua Teste 100	Apto 1	Porto Alegre	RS	90000000	BR	51999990000	2026-09-08 02:01:00.595838+00	2026-09-08 02:01:03.498094+00
c940cfc7-52ec-48be-a2e3-401ec5b4630d	ORD-BIATsmnYIygb3yt1_N1-mQ	47945c60-d869-4247-a49b-990f14cf3da5	paid	69800	pi_3UDELLRG5ULykWvo0YVNRAqB	\N	Admin Teste	Rua Teste 100	Apto 1	Porto Alegre	RS	90000000	BR	51999990000	2026-09-08 02:01:03.67381+00	2026-09-08 02:01:05.737455+00
\.


--
-- Data for Name: password_reset_tokens; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.password_reset_tokens (id, user_id, token_hash, expires_at, used_at, created_at) FROM stdin;
\.


--
-- Data for Name: products; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.products (id, name, description, price_cents, stock, image_url, category_id, active, created_at, updated_at) FROM stdin;
730caa90-d5df-4217-88a6-9d05ff56d2dd	Noise Cancelling Headphones	Over-ear wireless headphones with 30h battery and active noise cancelling.	24990	25	https://placehold.co/600x400?text=Headphones	0a0c3d20-92c5-4cde-9f55-26295e84ffbe	t	2026-09-08 02:00:55.274529+00	2026-09-08 02:00:55.274529+00
e3ce0112-3903-4d41-a690-ad49a90560a1	Mechanical Keyboard 75%	Hot-swappable mechanical keyboard, tactile switches, USB-C.	45900	12	https://placehold.co/600x400?text=Keyboard	0a0c3d20-92c5-4cde-9f55-26295e84ffbe	t	2026-09-08 02:00:55.277699+00	2026-09-08 02:00:55.277699+00
8c45b506-5b0c-4eb2-bd0f-33cfd761ab97	4K Webcam	Ultra HD webcam with autofocus and dual microphones.	39900	8	https://placehold.co/600x400?text=Webcam	0a0c3d20-92c5-4cde-9f55-26295e84ffbe	t	2026-09-08 02:00:55.279109+00	2026-09-08 02:00:55.279109+00
e3b89e31-b341-4001-98e3-44d834166855	Clean Architecture	A craftsman guide to software structure and design.	15900	40	https://placehold.co/600x400?text=Clean+Architecture	473273f6-a6a9-4b64-80ec-c70ab69d2fe0	t	2026-09-08 02:00:55.280165+00	2026-09-08 02:00:55.280165+00
c2a8a607-2411-4b47-a18c-99f95f973740	The Pragmatic Programmer	Your journey to mastery, 20th anniversary edition.	17900	30	https://placehold.co/600x400?text=Pragmatic+Programmer	473273f6-a6a9-4b64-80ec-c70ab69d2fe0	t	2026-09-08 02:00:55.281202+00	2026-09-08 02:00:55.281202+00
93b3cb75-2e3d-4c19-b1f1-04f678290317	Espresso Machine	15-bar pump espresso machine with steam wand.	89900	6	https://placehold.co/600x400?text=Espresso+Machine	fdfd5e31-0d0e-400a-b15c-423a7a7c8a17	t	2026-09-08 02:00:55.281944+00	2026-09-08 02:00:55.281944+00
5a3cb23c-cc5e-4698-843e-bf16bfdfe0aa	Cast Iron Skillet 12"	Pre-seasoned cast iron skillet, oven safe up to 260C.	12900	22	https://placehold.co/600x400?text=Skillet	fdfd5e31-0d0e-400a-b15c-423a7a7c8a17	t	2026-09-08 02:00:55.282742+00	2026-09-08 02:00:55.282742+00
e8b4cce9-c812-429c-b70e-b128512aae94	Merino Wool Sweater	Lightweight merino wool crewneck sweater, unisex.	29900	18	https://placehold.co/600x400?text=Sweater	2bc32d05-9a48-425e-9a42-5c3604ba06f0	t	2026-09-08 02:00:55.283479+00	2026-09-08 02:00:55.283479+00
962889b8-7f1b-46d9-a75d-aa2ac46c294c	Running Shoes	Neutral cushioning running shoes with breathable mesh upper.	34900	11	https://placehold.co/600x400?text=Running+Shoes	2bc32d05-9a48-425e-9a42-5c3604ba06f0	t	2026-09-08 02:00:55.284225+00	2026-09-08 02:01:05.737455+00
\.


--
-- Data for Name: reviews; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.reviews (id, product_id, user_id, rating, comment, created_at, updated_at) FROM stdin;
61f7117a-2a95-40ec-a206-9e442c76a720	962889b8-7f1b-46d9-a75d-aa2ac46c294c	bc1f742d-c169-4c82-9d6e-514aceee69b1	5	seed dast Usuario Comum	2026-09-08 02:01:03.515314+00	2026-09-08 02:01:03.515314+00
fe77dd4c-d427-44bd-aa67-9a90a39d2428	962889b8-7f1b-46d9-a75d-aa2ac46c294c	47945c60-d869-4247-a49b-990f14cf3da5	5	seed dast Admin Teste	2026-09-08 02:01:05.764403+00	2026-09-08 02:01:05.764403+00
\.


--
-- Data for Name: schema_migrations; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.schema_migrations (name, applied_at) FROM stdin;
001_init.sql	2026-09-08 02:00:54.626996+00
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.users (id, email, password_hash, name, role, address_line1, address_line2, city, state, postal_code, country, phone, created_at, updated_at) FROM stdin;
b351b340-afb3-4a7f-8d2c-137ec36a3a1d	admin@shop.test	<BCRYPT-REDIGIDO>	Store Admin	admin	\N	\N	\N	\N	\N	\N	\N	2026-09-08 02:00:55.267491+00	2026-09-08 02:00:55.267491+00
7a93546c-ee53-4c7d-84ae-8795a1ec782d	customer@shop.test	<BCRYPT-REDIGIDO>	Demo Customer	customer	\N	\N	\N	\N	\N	\N	\N	2026-09-08 02:00:55.269822+00	2026-09-08 02:00:55.269822+00
bc1f742d-c169-4c82-9d6e-514aceee69b1	user@test.com	<BCRYPT-REDIGIDO>	Usuario Comum	customer	\N	\N	\N	\N	\N	\N	\N	2026-09-08 02:01:00.500523+00	2026-09-08 02:01:00.500523+00
47945c60-d869-4247-a49b-990f14cf3da5	admin@test.com	<BCRYPT-REDIGIDO>	Admin Teste	admin	\N	\N	\N	\N	\N	\N	\N	2026-09-08 02:01:03.591946+00	2026-09-08 02:01:03.591946+00
\.


--
-- Name: cart_items cart_items_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.cart_items
    ADD CONSTRAINT cart_items_pkey PRIMARY KEY (id);


--
-- Name: cart_items cart_items_user_id_product_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.cart_items
    ADD CONSTRAINT cart_items_user_id_product_id_key UNIQUE (user_id, product_id);


--
-- Name: categories categories_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.categories
    ADD CONSTRAINT categories_name_key UNIQUE (name);


--
-- Name: categories categories_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.categories
    ADD CONSTRAINT categories_pkey PRIMARY KEY (id);


--
-- Name: categories categories_slug_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.categories
    ADD CONSTRAINT categories_slug_key UNIQUE (slug);


--
-- Name: order_items order_items_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.order_items
    ADD CONSTRAINT order_items_pkey PRIMARY KEY (id);


--
-- Name: orders orders_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_pkey PRIMARY KEY (id);


--
-- Name: orders orders_public_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_public_id_key UNIQUE (public_id);


--
-- Name: password_reset_tokens password_reset_tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.password_reset_tokens
    ADD CONSTRAINT password_reset_tokens_pkey PRIMARY KEY (id);


--
-- Name: password_reset_tokens password_reset_tokens_token_hash_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.password_reset_tokens
    ADD CONSTRAINT password_reset_tokens_token_hash_key UNIQUE (token_hash);


--
-- Name: products products_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.products
    ADD CONSTRAINT products_pkey PRIMARY KEY (id);


--
-- Name: reviews reviews_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_pkey PRIMARY KEY (id);


--
-- Name: reviews reviews_product_id_user_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_product_id_user_id_key UNIQUE (product_id, user_id);


--
-- Name: schema_migrations schema_migrations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.schema_migrations
    ADD CONSTRAINT schema_migrations_pkey PRIMARY KEY (name);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: cart_items_user_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX cart_items_user_idx ON public.cart_items USING btree (user_id);


--
-- Name: order_items_order_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX order_items_order_idx ON public.order_items USING btree (order_id);


--
-- Name: orders_user_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX orders_user_idx ON public.orders USING btree (user_id, created_at DESC);


--
-- Name: password_reset_tokens_user_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX password_reset_tokens_user_idx ON public.password_reset_tokens USING btree (user_id);


--
-- Name: products_category_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX products_category_idx ON public.products USING btree (category_id);


--
-- Name: products_name_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX products_name_idx ON public.products USING btree (lower(name));


--
-- Name: reviews_product_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX reviews_product_idx ON public.reviews USING btree (product_id);


--
-- Name: cart_items cart_items_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.cart_items
    ADD CONSTRAINT cart_items_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id) ON DELETE CASCADE;


--
-- Name: cart_items cart_items_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.cart_items
    ADD CONSTRAINT cart_items_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: order_items order_items_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.order_items
    ADD CONSTRAINT order_items_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders(id) ON DELETE CASCADE;


--
-- Name: order_items order_items_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.order_items
    ADD CONSTRAINT order_items_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id) ON DELETE SET NULL;


--
-- Name: orders orders_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: password_reset_tokens password_reset_tokens_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.password_reset_tokens
    ADD CONSTRAINT password_reset_tokens_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: products products_category_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.products
    ADD CONSTRAINT products_category_id_fkey FOREIGN KEY (category_id) REFERENCES public.categories(id) ON DELETE SET NULL;


--
-- Name: reviews reviews_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id) ON DELETE CASCADE;


--
-- Name: reviews reviews_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict XCri1puZQTC9iFmWtnT6BKT7orge8uehCdriEUravCx6gaMcBlkEsAVza0InGUy

