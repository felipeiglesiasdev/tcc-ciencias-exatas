-- --------------------------------------------------------
-- TABELA 'cnaes'
CREATE TABLE cnaes (
    codigo VARCHAR(10) NOT NULL,
    descricao VARCHAR(255) NOT NULL,
    PRIMARY KEY (codigo)
);
-- --------------------------------------------------------
-- TABELA `naturezas_juridicas`
CREATE TABLE naturezas_juridicas (
  codigo VARCHAR(4) NOT NULL,
  descricao varchar(255) NOT NULL,
  PRIMARY KEY (codigo)
);
-- --------------------------------------------------------
-- TABELA `municipios`
CREATE TABLE municipios (
  codigo VARCHAR(4) NOT NULL,
  descricao varchar(255) NOT NULL,
  PRIMARY KEY (codigo)
);
-- --------------------------------------------------------
-- Tabela `paises`
CREATE TABLE paises (
  codigo VARCHAR(3) NOT NULL,
  descricao varchar(255) NOT NULL,
  PRIMARY KEY (codigo)
);
-- --------------------------------------------------------
-- TABELA `qualificacoes_socios`
CREATE TABLE qualificacoes_socios (
  codigo varchar(2) NOT NULL,
  descricao varchar(255) NOT NULL,
  PRIMARY KEY (codigo)
);
-- --------------------------------------------------------
-- TABELA `empresas`
CREATE TABLE empresas (
  cnpj_basico varchar(8) NOT NULL,
  razao_social varchar(255) DEFAULT NULL,
  natureza_juridica VARCHAR(4) DEFAULT NULL,
  qualificacao_responsavel VARCHAR(2) DEFAULT NULL,
  capital_social decimal(18,2) DEFAULT NULL,
  porte_empresa int DEFAULT NULL,
  ente_federativo_responsavel varchar(255)  DEFAULT NULL,
  PRIMARY KEY (cnpj_basico),
  CONSTRAINT fk_empresas_natureza_juridica 
    FOREIGN KEY (natureza_juridica) REFERENCES naturezas_juridicas(codigo),
  CONSTRAINT fk_empresas_qualificacao_responsavel 
    FOREIGN KEY (qualificacao_responsavel) REFERENCES qualificacoes_socios(codigo)
);
-- --------------------------------------------------------
-- TABELA `estabelecimentos`
CREATE TABLE estabelecimentos (
  cnpj_basico varchar(8) NOT NULL,
  cnpj_ordem varchar(4) NOT NULL,
  cnpj_dv varchar(2) NOT NULL,
  identificador_matriz_filial int DEFAULT NULL,
  nome_fantasia varchar(255) DEFAULT NULL,
  situacao_cadastral int DEFAULT NULL,
  data_situacao_cadastral date DEFAULT NULL,
  motivo_situacao_cadastral int DEFAULT NULL,
  nome_cidade_exterior varchar(255) DEFAULT NULL,
  pais VARCHAR(3) DEFAULT NULL,
  data_inicio_atividade date DEFAULT NULL,
  cnae_fiscal_principal VARCHAR(10) DEFAULT NULL,
  cnae_fiscal_secundaria text,
  tipo_logradouro varchar(100) DEFAULT NULL,
  logradouro varchar(255) DEFAULT NULL,
  numero varchar(20) DEFAULT NULL,
  complemento varchar(255) DEFAULT NULL,
  bairro varchar(100) DEFAULT NULL,
  cep varchar(8) DEFAULT NULL,
  uf varchar(2) DEFAULT NULL,
  municipio VARCHAR(3) DEFAULT NULL,
  ddd1 varchar(4) DEFAULT NULL,
  telefone1 varchar(15) DEFAULT NULL,
  ddd2 varchar(4) DEFAULT NULL,
  telefone2 varchar(15) DEFAULT NULL,
  ddd_fax varchar(4) DEFAULT NULL,
  fax varchar(15) DEFAULT NULL,
  correio_eletronico varchar(255) DEFAULT NULL,
  situacao_especial varchar(255) DEFAULT NULL,
  data_situacao_especial date DEFAULT NULL,
  PRIMARY KEY (cnpj_basico, cnpj_ordem, cnpj_dv),
  CONSTRAINT fk_estab_cnpj_basico
    FOREIGN KEY (cnpj_basico) REFERENCES empresas(cnpj_basico),
  CONSTRAINT fk_estab_pais
    FOREIGN KEY (pais) REFERENCES paises(codigo),
  CONSTRAINT fk_estab_cnae_fiscal_principal
    FOREIGN KEY (cnae_fiscal_principal) REFERENCES cnaes(codigo),
  CONSTRAINT fk_estab_municipio
    FOREIGN KEY (municipio) REFERENCES municipios(codigo)
);
-- --------------------------------------------------------
-- TABELA `simples`
CREATE TABLE simples (
  cnpj_basico varchar(8) NOT NULL,
  opcao_pelo_simples char(1) DEFAULT NULL,
  data_opcao_pelo_simples date DEFAULT NULL,
  data_exclusao_do_simples date DEFAULT NULL,
  opcao_pelo_mei char(1) DEFAULT NULL,
  data_opcao_pelo_mei date DEFAULT NULL,
  data_exclusao_do_mei date DEFAULT NULL,
  PRIMARY KEY (cnpj_basico),
  CONSTRAINT fk_simples_cnpj_basico
    FOREIGN KEY (cnpj_basico) REFERENCES empresas(cnpj_basico)
);
-- --------------------------------------------------------
-- TABELA `socios`
CREATE TABLE socios (
  cnpj_basico varchar(8) NOT NULL,
  identificador_socio int DEFAULT NULL,
  nome_socio varchar(255) DEFAULT NULL,
  cnpj_cpf_socio varchar(14) NOT NULL,
  qualificacao_socio VARCHAR(2) DEFAULT NULL,
  data_entrada_sociedade date DEFAULT NULL,
  pais VARCHAR(3) DEFAULT NULL,
  representante_legal varchar(11) DEFAULT NULL,
  nome_representante varchar(255) DEFAULT NULL,
  qualificacao_representante_legal VARCHAR(2) DEFAULT NULL,
  faixa_etaria int DEFAULT NULL,
  PRIMARY KEY (cnpj_basico, cnpj_cpf_socio),
  CONSTRAINT fk_socio_cnpj_basico
    FOREIGN KEY (cnpj_basico) REFERENCES empresas(cnpj_basico),
  CONSTRAINT fk_socio_qualificacao_socio
    FOREIGN KEY (qualificacao_socio) REFERENCES qualificacoes_socios(codigo),
  CONSTRAINT fk_socio_qualificacao_representante_legal
    FOREIGN KEY (qualificacao_representante_legal) REFERENCES qualificacoes_socios(codigo)
);
-- --------------------------------------------------------
