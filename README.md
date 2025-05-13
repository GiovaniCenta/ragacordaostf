# Acórdão Claim Validator

This project validates claims made in summaries against original legal documents (Acórdãos from TCU - Brazilian Court of Accounts) using a RAG (Retrieval-Augmented Generation) pipeline. It operates as a command-line tool.

## Recent Updates

- **New Execution Environment**: Now configured to run on Google Colab with L4 GPU for improved performance.
- **Sentence-Level Claim Processing**: Added NLTK integration to split paragraphs in resumo files into individual sentences. This allows for granular claim validation instead of treating whole paragraphs as single claims.
- **Model Upgrade**: After extensive testing of multiple models, we've upgraded to **Qwen/QwQ-32B-AWQ** for claim validation, which significantly improves accuracy through better reasoning capabilities.
- **Domain-Specific Embedding & Reranking**: Replaced general multilingual models with **Legal-BERTimbau** for both embedding and reranking, improving retrieval precision for Brazilian legal texts.
- **Enhanced Result Output**: Now generating structured CSV files with detailed metrics for each claim validation.

##  Modules Description

*   **`main.py`**: The main script for running the validation process via the command line. It orchestrates the loading, retrieving, reranking, and validation steps for a given pair of Acórdão and Summary files.
*   **`src/data_loader.py`**: Handles loading and preprocessing of input documents (.txt and .pdf). It splits documents into paragraphs (chunks) and now splits paragraphs into sentences for more granular claim validation.
*   **`src/indexer.py`**: Responsible for creating or updating a vector index (using ChromaDB) from document chunks. It generates embeddings using a sentence-transformer model and stores them.
*   **`src/retriever.py`**: Queries the vector index to find document chunks relevant to a given query (claim). It uses sentence embeddings for similarity search.
*   **`src/reranker.py`**: Takes the initially retrieved chunks and reranks them using a more powerful Cross-Encoder model to improve the relevance ordering before sending them to the LLM.
*   **`src/llm_explainer.py`**: Uses Qwen/QwQ-32B-AWQ to validate claims against retrieved context and provide detailed justifications.

## Model Selection & Prompt Engineering

We tested multiple LLMs before selecting the final model:

- **Llama 3.1 7B**: Despite being a recent model, it struggled with nuanced legal reasoning and produced inconsistent outputs in Portuguese.
- **Mistral 7B**: Similar issues as Llama - inadequate reasoning on complex legal claims.
- **Gemma 2B**: The original model used, but produced lower quality justifications.
- **Qwen/QwQ-32B-AWQ (Selected)**: This larger model demonstrated superior reasoning capabilities and consistency in Portuguese legal text comprehension.

We also extensively experimented with prompt engineering:
- Tested various formats for presenting evidence paragraphs
- Refined the system instructions for clearer outputs
- Developed a reliable parsing technique for structured responses
- The current prompt format proved most effective at generating clear verdicts with substantiated rationales

## Setup and Running

### Dependencies

Install the required Python packages:

```bash
pip install -r requirements.txt
```

*(Note: For the Qwen model, specific dependencies like `autoawq` are required for 4-bit quantization which significantly reduces VRAM requirements while maintaining performance.)*

### Running the Command-Line Tool

The `main.py` script validates all claims in a summary file against an Acórdão file.

#### Google Colab (Recommended)

The easiest way to run this application is using Google Colab with an L4 GPU:

```bash
python main.py --pdf_file "data/Acórdão 764 de 2025 Plenário.pdf" \
              --resumo_file "data/Acórdão 764-2025 resumos.txt" \
              --csv_results_file "Acordao 764-2025 resultados.csv" \
              --csv_justifications_file "Acordao 764-2025 justificativas.csv"
```

#### Local Execution

If running locally, use:

```bash
python main.py --acordao_file path/to/acordao.pdf --resumo_file path/to/resumo.txt --output_dir results_folder
```

*   `--acordao_file`: Path to the main Acórdão document (.pdf or .txt). Defaults to `data/Acórdão 733 de 2025 Plenário.pdf`.
*   `--resumo_file`: Path to the summary file (.txt). Defaults to `data/Acórdão 733-2025 resumos.txt`.
*   `--output_dir`: Directory to save the validation results. Three files will be generated:
    * A human-readable TXT summary
    * A CSV file with claim validation results
    * A CSV file with detailed justifications

The script requires a ChromaDB index to exist (created by the indexing step in the first run). The ChromaDB index will be saved in the `chroma_db_index` directory by default.

### Running with Docker

The easiest way to run the application is using Docker.

1.  **Build the Docker image:**
    ```bash
    docker build -t acordao-validator .
    ```

2.  **Create persistent volumes (optional but recommended):** This prevents re-downloading models and re-creating the index every time the container starts.
    ```bash
    docker volume create chroma_db_vol
    docker volume create hf_cache_vol
    docker volume create results_vol
    ```

3.  **Run the Docker container:**
    *   **With persistent volumes:**
        ```bash
        docker run \
          -v chroma_db_vol:/app/chroma_db_index \
          -v hf_cache_vol:/app/.cache/huggingface \
          -v results_vol:/app/results \
          -v /path/to/your/data:/app/data \
          --name acordao-validator-app \
          acordao-validator
        ```
    *   **With custom input files:**
        ```bash
        docker run \
          -v chroma_db_vol:/app/chroma_db_index \
          -v hf_cache_vol:/app/.cache/huggingface \
          -v results_vol:/app/results \
          -v /path/to/your/data:/app/data \
          --name acordao-validator-app \
          acordao-validator \
          --acordao_file data/your_acordao.pdf \
          --resumo_file data/your_resumo.txt
        ```

## Test Configuration and Minimum Requirements

### Current Configuration

This application is now configured to run optimally on:

* **Google Colab with L4 GPU**: Provides sufficient computational resources for running the Qwen model.

### Previous Test Configuration

This application was originally developed and tested on the following configuration:

*   **GPU:** NVIDIA GeForce GTX 1660 SUPER (6GB VRAM)
*   **CPU:** Intel Core i5-8400
*   **RAM:** 16GB System Memory
*   **OS:** Windows (via Docker Desktop)

### Minimum Requirements (Estimated)

Running this application, especially the Qwen 32B model (even with AWQ quantization), requires significant computational resources:

*   **GPU:** A CUDA-enabled NVIDIA GPU is **required** for acceptable performance.
    *   **VRAM:** Minimum 8GB VRAM for running the quantized Qwen model. 12GB+ VRAM is preferable.
    *   **CUDA Compute Capability:** 7.5+ recommended for optimal AWQ support.
*   **RAM:** 16GB of system RAM minimum, 32GB recommended.
*   **CPU:** A modern multi-core processor (equivalent to Intel i5 8th Gen or better).
*   **Disk Space:** Sufficient free space for:
    *   Docker images (several GB).
    *   Hugging Face model cache (~20GB for all models).
    *   ChromaDB vector index (size depends on the amount of data indexed).
*   **OS:** Linux, macOS, or Windows with Docker support.

*Note: Running without a dedicated GPU is not feasible for this configuration due to the LLM size.*

## Model Choices

*   **Embedding Model (`rufimelo/Legal-BERTimbau-sts-large`):**
    *   **Portuguese Legal Domain:** Specifically fine-tuned for Brazilian legal text, offering better performance than general multilingual models.
    *   **Size:** The `large` version balances performance and resource requirements.
    *   **Improved Retrieval:** Domain adaptation significantly enhances the quality of retrieved paragraphs compared to general multilingual embeddings.

*   **Reranker Model (`rufimelo/Legal-BERTimbau-sts-large` as CrossEncoder):**
    *   **Portuguese Legal Domain Specialization:** Using the same model architecture as a cross-encoder for reranking provides domain-specific relevance scoring.
    *   **Efficiency:** Using a reranker on a small set of initially retrieved candidates is much more efficient than direct cross-encoder search.
    *   **Consistency:** Using the same model for both embedding and reranking ensures conceptual alignment throughout the retrieval pipeline.

*   **LLM (`Qwen/QwQ-32B-AWQ`):**
    *   **Size and Performance:** At 32B parameters (quantized to 4-bit with AWQ), this model provides excellent reasoning capabilities while maintaining reasonable hardware requirements.
    *   **Multilingual Capabilities:** Strong performance on Portuguese legal text.
    *   **Reasoning:** Superior ability to analyze complex legal claims against evidence.
    *   **Efficient Implementation:** AWQ quantization reduces memory requirements while preserving model quality.

## Future Adjustments

*   **Fine-tuning for Legal Domain:** 
    *   Create a specialized fine-tuned version of the LLM specifically for Portuguese legal claim validation.
    *   Develop training datasets using Acórdãos retrieved from the STF (Brazilian Supreme Court) API to further improve domain adaptation.
*   **Advanced RAG Techniques:**
    *   **Query Expansion/Transformation:** Use an LLM to refine or expand user queries for better retrieval.
    *   **Self-Correction/Self-RAG:** Implement techniques where the LLM can self-critique its answers or trigger re-retrieval if the initial context is insufficient.
    *   **Hybrid Search:** Combine dense vector search with traditional keyword search (e.g., BM25).
*   **Evaluation Framework:** Develop a more robust framework for evaluating the end-to-end accuracy and performance of the validation pipeline.
*   **Configuration:** Allow easier configuration of models, thresholds, and paths (e.g., via a config file or environment variables).
*   **Error Handling:** Improve error handling and reporting throughout the application.
*   **Standalone Indexing Script:** Create a dedicated script for indexing documents without running the full validation pipeline.

---

# Validador de Alegações de Acórdãos (Português)

Este projeto valida alegações feitas em resumos contra documentos jurídicos originais (Acórdãos do TCU - Tribunal de Contas da União) usando um pipeline RAG (Retrieval-Augmented Generation). Funciona como uma ferramenta de linha de comando.

## Atualizações Recentes

- **Novo Ambiente de Execução**: Agora configurado para rodar no Google Colab com GPU L4 para melhor desempenho.
- **Processamento de Alegações em Nível de Sentença**: Adicionada integração do NLTK para dividir parágrafos em arquivos de resumo em sentenças individuais. Isso permite uma validação de alegações mais granular, em vez de tratar parágrafos inteiros como alegações únicas.
- **Atualização de Modelo**: Após testes extensivos de múltiplos modelos, atualizamos para **Qwen/QwQ-32B-AWQ** para validação de alegações, o que melhora significativamente a precisão através de melhores capacidades de raciocínio.
- **Embeddings e Reranking Específicos para Domínio Jurídico**: Substituímos modelos multilíngues gerais pelo **Legal-BERTimbau** tanto para embeddings quanto para reranking, melhorando a precisão da recuperação para textos jurídicos brasileiros.
- **Saída de Resultados Aprimorada**: Agora gerando arquivos CSV estruturados com métricas detalhadas para cada validação de alegação.

## Descrição dos Módulos

*   **`main.py`**: O script principal para executar o processo de validação via linha de comando. Ele orquestra as etapas de carregamento, recuperação, reordenação e validação para um par de arquivos de Acórdão e Resumo fornecido.
*   **`src/data_loader.py`**: Lida com o carregamento e pré-processamento de documentos de entrada (.txt e .pdf). Divide os documentos em parágrafos e agora divide parágrafos em sentenças para uma validação de alegações mais granular.
*   **`src/indexer.py`**: Responsável por criar ou atualizar um índice vetorial (usando ChromaDB) a partir dos chunks do documento. Gera embeddings usando um modelo sentence-transformer e os armazena.
*   **`src/retriever.py`**: Consulta o índice vetorial para encontrar chunks de documento relevantes para uma determinada consulta (alegação). Usa embeddings de sentenças para busca por similaridade.
*   **`src/reranker.py`**: Pega os chunks recuperados inicialmente e os reordena usando um modelo Cross-Encoder mais poderoso para melhorar a ordem de relevância antes de enviá-los para o LLM.
*   **`src/llm_explainer.py`**: Usa Qwen/QwQ-32B-AWQ para validar alegações contra o contexto recuperado e fornecer justificativas detalhadas.

## Seleção de Modelo e Engenharia de Prompt

Testamos múltiplos LLMs antes de selecionar o modelo final:

- **Llama 3.1 7B**: Apesar de ser um modelo recente, ele teve dificuldades com raciocínio jurídico nuançado e produziu saídas inconsistentes em português.
- **Mistral 7B**: Problemas similares ao Llama - raciocínio inadequado em alegações jurídicas complexas.
- **Gemma 2B**: O modelo original usado, mas produziu justificativas de qualidade inferior.
- **Qwen/QwQ-32B-AWQ (Selecionado)**: Este modelo maior demonstrou capacidades de raciocínio superiores e consistência na compreensão de texto jurídico em português.

Também experimentamos extensivamente com engenharia de prompt:
- Testamos vários formatos para apresentar parágrafos de evidência
- Refinamos as instruções do sistema para saídas mais claras
- Desenvolvemos uma técnica de análise confiável para respostas estruturadas
- O formato de prompt atual provou ser mais eficaz na geração de vereditos claros com fundamentos substanciados

## Configuração e Execução

### Dependências

Instale os pacotes Python necessários:

```bash
pip install -r requirements.txt
```

*(Observação: Para o modelo Qwen, dependências específicas como `autoawq` são necessárias para quantização de 4 bits, o que reduz significativamente os requisitos de VRAM enquanto mantém o desempenho.)*

### Executando a Ferramenta de Linha de Comando

O script `main.py` valida todas as alegações em um arquivo de resumo contra um arquivo de Acórdão.

#### Google Colab (Recomendado)

A maneira mais fácil de executar esta aplicação é usando o Google Colab com uma GPU L4:

```bash
python main.py --pdf_file "data/Acórdão 764 de 2025 Plenário.pdf" \
              --resumo_file "data/Acórdão 764-2025 resumos.txt" \
              --csv_results_file "Acordao 764-2025 resultados.csv" \
              --csv_justifications_file "Acordao 764-2025 justificativas.csv"
```

#### Execução Local

Se estiver executando localmente, use:

```bash
python main.py --acordao_file caminho/para/acordao.pdf --resumo_file caminho/para/resumo.txt --output_dir pasta_resultados
```

*   `--acordao_file`: Caminho para o documento principal do Acórdão (.pdf ou .txt). Padrão: `data/Acórdão 733 de 2025 Plenário.pdf`.
*   `--resumo_file`: Caminho para o arquivo de resumo (.txt). Padrão: `data/Acórdão 733-2025 resumos.txt`.
*   `--output_dir`: Diretório para salvar os resultados da validação. Três arquivos serão gerados:
    * Um resumo TXT legível por humanos
    * Um arquivo CSV com resultados de validação de alegações
    * Um arquivo CSV com justificativas detalhadas

O script requer que um índice ChromaDB exista (criado na primeira execução). O índice ChromaDB será salvo no diretório `chroma_db_index` por padrão.

### Executando com Docker

A maneira mais fácil de executar a aplicação é usando Docker.

1.  **Construa a imagem Docker:**
    ```bash
    docker build -t acordao-validator .
    ```

2.  **Crie volumes persistentes (opcional, mas recomendado):** Isso evita baixar novamente os modelos e recriar o índice toda vez que o contêiner for iniciado.
    ```bash
    docker volume create chroma_db_vol
    docker volume create hf_cache_vol
    docker volume create results_vol
    ```

3.  **Execute o contêiner Docker:**
    *   **Com volumes persistentes:**
        ```bash
        docker run \
          -v chroma_db_vol:/app/chroma_db_index \
          -v hf_cache_vol:/app/.cache/huggingface \
          -v results_vol:/app/results \
          -v /caminho/para/seus/dados:/app/data \
          --name acordao-validator-app \
          acordao-validator
        ```
    *   **Com arquivos de entrada personalizados:**
        ```bash
        docker run \
          -v chroma_db_vol:/app/chroma_db_index \
          -v hf_cache_vol:/app/.cache/huggingface \
          -v results_vol:/app/results \
          -v /caminho/para/seus/dados:/app/data \
          --name acordao-validator-app \
          acordao-validator \
          --acordao_file data/seu_acordao.pdf \
          --resumo_file data/seu_resumo.txt
        ```

## Configuração de Teste e Requisitos Mínimos

### Configuração Atual

Esta aplicação está agora configurada para executar de forma ideal em:

* **Google Colab com GPU L4**: Fornece recursos computacionais suficientes para executar o modelo Qwen.

### Configuração de Teste Anterior

Esta aplicação foi originalmente desenvolvida e testada na seguinte configuração:

*   **GPU:** NVIDIA GeForce GTX 1660 SUPER (6GB VRAM)
*   **CPU:** Intel Core i5-8400
*   **RAM:** 16GB de Memória do Sistema
*   **SO:** Windows (via Docker Desktop)

### Requisitos Mínimos (Estimados)

Executar esta aplicação, especialmente o modelo Qwen 32B (mesmo com quantização AWQ), requer recursos computacionais significativos:

*   **GPU:** Uma GPU NVIDIA habilitada para CUDA é **necessária** para desempenho aceitável.
    *   **VRAM:** Mínimo de 8GB VRAM para executar o modelo Qwen quantizado. 12GB+ VRAM é preferível.
    *   **Capacidade de Computação CUDA:** 7.5+ recomendado para suporte AWQ ideal.
*   **RAM:** 16GB de RAM do sistema mínimo, 32GB recomendados.
*   **CPU:** Um processador multi-core moderno (equivalente a Intel i5 de 8ª geração ou superior).
*   **Espaço em Disco:** Espaço livre suficiente para:
    *   Imagens Docker (vários GB).
    *   Cache de modelos Hugging Face (~20GB para todos os modelos).
    *   Índice vetorial ChromaDB (tamanho depende da quantidade de dados indexados).
*   **SO:** Linux, macOS ou Windows com suporte a Docker.

*Observação: Executar sem uma GPU dedicada não é viável para esta configuração devido ao tamanho do LLM.*

## Escolha dos Modelos

*   **Modelo de Embedding (`rufimelo/Legal-BERTimbau-sts-large`):**
    *   **Domínio Jurídico Português:** Especificamente ajustado para texto jurídico brasileiro, oferecendo melhor desempenho que modelos multilíngues gerais.
    *   **Tamanho:** A versão `large` equilibra desempenho e requisitos de recursos.
    *   **Recuperação Aprimorada:** A adaptação ao domínio melhora significativamente a qualidade dos parágrafos recuperados em comparação com embeddings multilíngues gerais.

*   **Modelo Reranker (`rufimelo/Legal-BERTimbau-sts-large` como CrossEncoder):**
    *   **Especialização em Domínio Jurídico Português:** Usar a mesma arquitetura de modelo como cross-encoder para reordenação fornece pontuação de relevância específica do domínio.
    *   **Eficiência:** Usar um reranker em um pequeno conjunto de candidatos inicialmente recuperados é muito mais eficiente que a busca direta por cross-encoder.
    *   **Consistência:** Usar o mesmo modelo para embedding e reranking garante alinhamento conceitual em todo o pipeline de recuperação.

*   **LLM (`Qwen/QwQ-32B-AWQ`):**
    *   **Tamanho e Desempenho:** Com 32B de parâmetros (quantizados para 4 bits com AWQ), este modelo fornece excelentes capacidades de raciocínio enquanto mantém requisitos de hardware razoáveis.
    *   **Capacidades Multilíngues:** Forte desempenho em texto jurídico em português.
    *   **Raciocínio:** Capacidade superior de analisar alegações jurídicas complexas contra evidências.
    *   **Implementação Eficiente:** A quantização AWQ reduz os requisitos de memória enquanto preserva a qualidade do modelo.

## Ajustes Futuros

*   **Fine-tuning para Domínio Jurídico:** 
    *   Criar uma versão fine-tuned especializada do LLM especificamente para validação de alegações jurídicas em português.
    *   Desenvolver datasets de treinamento usando Acórdãos obtidos da API do STF (Supremo Tribunal Federal) para melhorar ainda mais a adaptação ao domínio.
*   **Técnicas Avançadas de RAG:**
    *   **Expansão/Transformação de Consulta:** Usar um LLM para refinar ou expandir consultas de usuário para melhor recuperação.
    *   **Autocorreção/Self-RAG:** Implementar técnicas onde o LLM pode autocriticar suas respostas ou acionar nova recuperação se o contexto inicial for insuficiente.
    *   **Busca Híbrida:** Combinar busca vetorial densa com busca tradicional por palavras-chave (por exemplo, BM25).
*   **Framework de Avaliação:** Desenvolver um framework mais robusto para avaliar a precisão e o desempenho de ponta a ponta do pipeline de validação.
*   **Configuração:** Permitir configuração mais fácil de modelos, limiares e caminhos (por exemplo, via arquivo de configuração ou variáveis de ambiente).
*   **Tratamento de Erros:** Melhorar o tratamento e o relatório de erros em toda a aplicação.
*   **Script de Indexação Autônomo:** Criar um script dedicado para indexar documentos sem executar o pipeline completo de validação. 