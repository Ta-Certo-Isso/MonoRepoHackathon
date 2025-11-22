"""
Coletor Principal - Montoya
Integra todas as fontes de dados: Federal (API), Estadual (Scraping), Municipal (Scraping)
"""

import sys
import io
import json
import time
from typing import Dict, List
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# Importa os coletores
from coletor_federal_camara import ColetorCamara
from coletor_federal_senado import ColetorSenado
from coletor_estadual import ColetorALESP
from coletor_municipal import ColetorMunicipal

# Lock para prints thread-safe
print_lock = Lock()


class ColetorMontoya:
    """Coletor principal que integra todas as fontes"""
    
    def __init__(self) -> None:
        """Inicializa todos os coletores"""
        self.coletor_camara = ColetorCamara()
        self.coletor_senado = ColetorSenado()
        self.coletor_alesp = ColetorALESP()
        self.coletor_municipal = ColetorMunicipal()
        
    def _coletar_camara(self, dias_atras: int, limite: int) -> tuple:
        """Coleta da Câmara dos Deputados"""
        with print_lock:
            print("[THREAD] Iniciando coleta da Camara dos Deputados...")
            sys.stdout.flush()
        inicio = time.time()
        try:
            proposicoes = self.coletor_camara.buscar_proposicoes_recentes(
                sigla_tipo='PL',
                dias_atras=dias_atras,
                limite=limite
            )
            for prop in proposicoes:
                prop['nivel'] = 'federal'
                prop['fonte'] = 'camara_deputados'
                prop['tipo_coleta'] = 'api'
            tempo = time.time() - inicio
            with print_lock:
                print(f"[THREAD] Camara concluida em {tempo:.2f}s - {len(proposicoes)} proposicoes")
                sys.stdout.flush()
            return ('federal_camara', proposicoes)
        except Exception as e:
            tempo = time.time() - inicio
            with print_lock:
                print(f"[THREAD] [ERRO] Camara falhou em {tempo:.2f}s: {e}")
                sys.stdout.flush()
            return ('federal_camara', [])
    
    def _coletar_senado(self, dias_atras: int, limite: int) -> tuple:
        """Coleta do Senado Federal"""
        with print_lock:
            print("[THREAD] Iniciando coleta do Senado Federal...")
        inicio = time.time()
        try:
            materias = self.coletor_senado.buscar_materias_recentes(
                dias_atras=dias_atras,
                limite=limite
            )
            for materia in materias:
                materia['nivel'] = 'federal'
                materia['fonte'] = 'senado_federal'
                materia['tipo_coleta'] = 'api'
            tempo = time.time() - inicio
            with print_lock:
                print(f"[THREAD] Senado concluido em {tempo:.2f}s - {len(materias)} materias")
                sys.stdout.flush()
            return ('federal_senado', materias)
        except Exception as e:
            tempo = time.time() - inicio
            with print_lock:
                print(f"[THREAD] [ERRO] Senado falhou em {tempo:.2f}s: {e}")
                sys.stdout.flush()
            return ('federal_senado', [])
    
    def _coletar_alesp(self, dias_atras: int, limite: int) -> tuple:
        """Coleta da ALESP"""
        with print_lock:
            print("[THREAD] Iniciando coleta da ALESP...")
        inicio = time.time()
        try:
            proposicoes = self.coletor_alesp.buscar_proposicoes_recentes(
                dias_atras=dias_atras,
                limite=limite
            )
            tempo = time.time() - inicio
            with print_lock:
                print(f"[THREAD] ALESP concluida em {tempo:.2f}s - {len(proposicoes)} proposicoes")
                sys.stdout.flush()
            return ('estadual_alesp', proposicoes)
        except Exception as e:
            tempo = time.time() - inicio
            with print_lock:
                print(f"[THREAD] [ERRO] ALESP falhou em {tempo:.2f}s: {e}")
                sys.stdout.flush()
            return ('estadual_alesp', [])
    
    def _coletar_municipal(self, dias_atras: int, limite: int) -> tuple:
        """Coleta de dados municipais via Google Search"""
        with print_lock:
            print("[THREAD] Iniciando coleta municipal (Google Search)...")
            sys.stdout.flush()
        inicio = time.time()
        try:
            proposicoes = self.coletor_municipal.buscar_proposicoes_recentes(
                regiao="Vale do Paraíba",
                dias_atras=dias_atras,
                limite=limite
            )
            tempo = time.time() - inicio
            with print_lock:
                print(f"[THREAD] Municipal concluida em {tempo:.2f}s - {len(proposicoes)} proposicoes")
                sys.stdout.flush()
            return ('municipal', proposicoes)
        except Exception as e:
            tempo = time.time() - inicio
            with print_lock:
                print(f"[THREAD] [ERRO] Municipal falhou em {tempo:.2f}s: {e}")
                sys.stdout.flush()
            return ('municipal', [])
    
    def coletar_todas_fontes(
        self,
        dias_atras: int = 30,
        limite_por_fonte: int = 10,
        incluir_municipios: bool = True,
        max_workers: int = 10
    ) -> Dict[str, List[Dict]]:
        """
        Coleta dados de todas as fontes disponíveis usando paralelização
        
        Args:
            dias_atras: Quantos dias atrás buscar
            limite_por_fonte: Limite de resultados por fonte
            incluir_municipios: Se deve incluir dados municipais
            max_workers: Número máximo de threads paralelas
            
        Returns:
            Dicionário com dados de cada fonte
        """
        resultados = {
            'federal_camara': [],      # Proposições da Câmara (API)
            'federal_senado': [],      # Proposições do Senado (API)
            'estadual_alesp': [],      # Notícias sobre ALESP (Google Search)
            'municipal': []            # Notícias municipais (Google Search)
            # Removido 'noticias' genérico - agora separado por nível
        }
        
        print("=" * 70)
        print("COLETOR MONTOYA - COLETANDO DE TODAS AS FONTES (PARALELO)")
        print("=" * 70)
        print(f"[INFO] Usando ate {max_workers} threads paralelas")
        print(f"[INFO] Periodo: ultimos {dias_atras} dias")
        print(f"[INFO] Limite por fonte: {limite_por_fonte}")
        print()
        sys.stdout.flush()
        
        inicio_total = time.time()
        
        # Prepara tarefas para paralelização
        tarefas = []
        
        # Tarefas principais (federais, estadual e municipal)
        tarefas.append(('federal_camara', self._coletar_camara, dias_atras, limite_por_fonte))
        tarefas.append(('federal_senado', self._coletar_senado, dias_atras, limite_por_fonte))
        tarefas.append(('estadual_alesp', self._coletar_alesp, dias_atras, limite_por_fonte))
        
        # Municipal (se incluir municípios)
        if incluir_municipios:
            tarefas.append(('municipal', self._coletar_municipal, dias_atras, limite_por_fonte))
        
        # Executa tarefas principais em paralelo
        print("[INFO] Iniciando coletas paralelas das fontes principais...")
        sys.stdout.flush()
        with ThreadPoolExecutor(max_workers=min(len(tarefas), max_workers)) as executor:
            futures = {}
            for nome, funcao, *args in tarefas:
                future = executor.submit(funcao, *args)
                futures[future] = nome
            
            # Aguarda conclusão e coleta resultados
            for future in as_completed(futures):
                nome_esperado = futures[future]
                try:
                    nome, dados = future.result(timeout=120)  # Timeout de 2 minutos por tarefa
                    resultados[nome] = dados
                    with print_lock:
                        print(f"[OK] {nome_esperado}: {len(dados)} itens coletados")
                        sys.stdout.flush()
                except Exception as e:
                    with print_lock:
                        print(f"[ERRO] {nome_esperado} falhou: {e}")
                        sys.stdout.flush()
        
        # Notícias municipais já foram coletadas na tarefa acima
        # Web scraping direto desativado - sites bloqueiam bots
        
        tempo_total = time.time() - inicio_total
        print("\n" + "=" * 70)
        print(f"[OK] Coleta concluida em {tempo_total:.2f} segundos")
        print("=" * 70)
        print()
        sys.stdout.flush()
        
        return resultados
    
    def filtrar_relevantes(self, resultados: Dict[str, List[Dict]]) -> Dict[str, List[Dict]]:
        """
        Filtra proposições relevantes de cada fonte
        
        Args:
            resultados: Resultados brutos da coleta
            
        Returns:
            Resultados filtrados
        """
        resultados_filtrados = {}
        
        # Filtra Câmara
        if resultados.get('federal_camara'):
            resultados_filtrados['federal_camara'] = self.coletor_camara.filtrar_por_relevancia(
                resultados['federal_camara']
            )
        
        # Filtra Senado
        if resultados.get('federal_senado'):
            resultados_filtrados['federal_senado'] = self.coletor_senado.filtrar_por_relevancia(
                resultados['federal_senado']
            )
        
        # Filtra ALESP
        if resultados.get('estadual_alesp'):
            resultados_filtrados['estadual_alesp'] = resultados.get('estadual_alesp', [])
        
        # Filtra Municipal
        if resultados.get('municipal'):
            resultados_filtrados['municipal'] = self.coletor_municipal.filtrar_por_relevancia(
                resultados['municipal']
            )
        
        return resultados_filtrados
    
    def gerar_resumo(self, resultados: Dict[str, List[Dict]]) -> Dict:
        """
        Gera um resumo dos dados coletados
        
        Args:
            resultados: Resultados da coleta
            
        Returns:
            Dicionário com resumo
        """
        total_por_fonte = {
            'federal_camara': len(resultados.get('federal_camara', [])),
            'federal_senado': len(resultados.get('federal_senado', [])),
            'estadual_alesp': len(resultados.get('estadual_alesp', [])),
            'municipal': len(resultados.get('municipal', []))
        }
        
        total_geral = sum(total_por_fonte.values())
        
        return {
            'data_coleta': datetime.now().isoformat(),
            'total_geral': total_geral,
            'total_por_fonte': total_por_fonte,
            'fontes_funcionando': [fonte for fonte, total in total_por_fonte.items() if total > 0]
        }


def main() -> None:
    """Função principal - configuração padrão"""
    # Configura encoding para Windows e força flush imediato
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', line_buffering=True)
    
    # Força flush imediato em todos os prints
    def print_flush(*args, **kwargs):
        print(*args, **kwargs)
        sys.stdout.flush()
    
    # ============================================================
    # CONFIGURAÇÕES - Ajuste aqui conforme necessário
    # ============================================================
    DIAS_ATRAS = 30                    # Quantos dias atrás buscar
    LIMITE_POR_FONTE = 10              # Limite de resultados por fonte
    INCLUIR_MUNICIPIOS = True          # Incluir dados municipais
    MAX_WORKERS = 10                   # Número máximo de threads paralelas
    # ============================================================
    
    try:
        print_flush("=" * 70)
        print_flush("COLETOR MONTOYA - INICIANDO")
        print_flush("=" * 70)
        print_flush("[INICIO] Iniciando coletor principal...")
        print_flush(f"[CONFIG] Periodo: ultimos {DIAS_ATRAS} dias")
        print_flush(f"[CONFIG] Limite por fonte: {LIMITE_POR_FONTE}")
        print_flush(f"[CONFIG] Municipios: {'Sim' if INCLUIR_MUNICIPIOS else 'Nao'}")
        print_flush(f"[CONFIG] Threads paralelas: {MAX_WORKERS}")
        print_flush()
        
        print_flush("[INFO] Criando instancias dos coletores...")
        coletor = ColetorMontoya()
        print_flush("[OK] Coletores inicializados\n")
        
        # Coleta de todas as fontes
        print_flush("[INFO] Iniciando coleta de todas as fontes...")
        resultados = coletor.coletar_todas_fontes(
            dias_atras=DIAS_ATRAS,
            limite_por_fonte=LIMITE_POR_FONTE,
            incluir_municipios=INCLUIR_MUNICIPIOS,
            max_workers=MAX_WORKERS
        )
        print_flush("[OK] Coleta de todas as fontes concluida\n")
        
        # Filtra relevantes
        print_flush("=" * 70)
        print_flush("FILTRANDO PROPOSICOES RELEVANTES...")
        print_flush("=" * 70)
        resultados_filtrados = coletor.filtrar_relevantes(resultados)
        print_flush("[OK] Filtragem concluida\n")
        
        # Gera resumo
        resumo = coletor.gerar_resumo(resultados_filtrados)
        
        # Mostra resumo
        print_flush("=" * 70)
        print_flush("RESUMO DA COLETA")
        print_flush("=" * 70)
        print_flush(f"Data: {resumo['data_coleta']}")
        print_flush(f"Total geral: {resumo['total_geral']} proposicoes")
        print_flush("\nPor fonte:")
        for fonte, total in resumo['total_por_fonte'].items():
            status = "[OK]" if total > 0 else "[VAZIO]"
            print_flush(f"  {status} {fonte}: {total}")
        
        print_flush(f"\nFontes funcionando: {len(resumo['fontes_funcionando'])}/{len(resumo['total_por_fonte'])}")
        
        # Salva resultados em JSON
        print_flush("\n" + "=" * 70)
        print_flush("Salvando resultados em 'resultados_coleta.json'...")
        try:
            with open('resultados_coleta.json', 'w', encoding='utf-8') as f:
                json.dump({
                    'resumo': resumo,
                    'dados': resultados_filtrados
                }, f, indent=2, ensure_ascii=False)
            print_flush("[OK] Resultados salvos em 'resultados_coleta.json'!")
        except Exception as e:
            print_flush(f"[ERRO] Erro ao salvar arquivo: {e}")
        
        print_flush("\n" + "=" * 70)
        print_flush("[FIM] Execucao concluida com sucesso!")
        print_flush("=" * 70)
        
    except KeyboardInterrupt:
        print_flush("\n[AVISO] Execucao interrompida pelo usuario")
        sys.exit(1)
    except Exception as e:
        print_flush(f"\n[ERRO CRITICO] Erro na execucao: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

