from dataclasses import dataclass, field
import os
from pathlib import Path
import sys
import pandas as pd


@dataclass
class uczen:
    name: str
    number: int
    grupy: list = field(default_factory=list)  

def save_to_django(uczniowie: list):
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Pkplan.settings")
    import django
    django.setup()

    from pkstudent.models import Group_types, Student, Student_Group

    sekcje = {
        sekcja.casefold(): (typ_grupy.name, sekcja)
        for typ_grupy in Group_types
        for sekcja in typ_grupy.section
    }

    for uczen_obj in uczniowie:
        student, created = Student.objects.get_or_create(number=int(uczen_obj.number))
        if created:
            print(f"Utworzono nowego studenta, Numer: {student.number}")
        else:
            print(f"Student już istnieje: Numer: {student.number}")

        grupy_do_zapisu = []
        for nazwa_sekcji in uczen_obj.grupy:
            typ_grupy, sekcja = sekcje[nazwa_sekcji.casefold()]
            grupa, _ = Student_Group.objects.get_or_create(
                groups=typ_grupy,
                section=sekcja,
            )
            grupy_do_zapisu.append(grupa)

        student.student_groups.set(grupy_do_zapisu)
        print(f"Zaktualizowano grupy dla numeru {student.number}: {uczen_obj.grupy}")

def nadaj_grupy_w(lista_uczniow: list):
    if not lista_uczniow:
        return
        
    for uczen_obj in lista_uczniow:
        # Sprawdzamy, czy numer nie jest pusty (NaN z Excela)
        if uczen_obj.number and pd.notna(uczen_obj.number):
            if int(uczen_obj.number) <= 98:
                uczen_obj.grupy.append("W1")
            else:
                uczen_obj.grupy.append("W2")

def nadaj_grupy_z_arkusza(lista_uczniow: list, sciezka_do_arkusza: str):
    if not lista_uczniow:
        print("Lista uczniów jest pusta.")
        return
    
    try:
        df = pd.read_excel(sciezka_do_arkusza, header=None)
        
        podzial_na_grupy = {}

        def normalizuj_imie(imie):
            return " ".join(str(imie).split()).casefold()

        for indeks_kolumny, grupa in enumerate(df.iloc[0]):
            if pd.isna(grupa) or not any(znak.isdigit() for znak in str(grupa)):
                continue

            grupa = str(grupa).strip()
            uczniowie_w_kolumnie = [
                normalizuj_imie(imie)
                for imie in df.iloc[1:, indeks_kolumny]
                if pd.notna(imie)
            ]
            podzial_na_grupy[grupa] = uczniowie_w_kolumnie
            print(f"Znaleziono grupę: {grupa}")
            
        print("Pomyślnie pogrupowano uczniów.")
        print("Podział na grupy:", podzial_na_grupy)
        
        for uczen_obj in lista_uczniow:
            for grupa, uczniowie in podzial_na_grupy.items():
                if normalizuj_imie(uczen_obj.name) in uczniowie:
                    uczen_obj.grupy.extend(
                        podgrupa.strip() for podgrupa in grupa.split("/")
                    )
                    
        return podzial_na_grupy
            
    except FileNotFoundError:
        print(f"Błąd: Nie znaleziono pliku {sciezka_do_arkusza}")
        return None

def wczytaj_uczniow(sciezka_do_pliku):
    try:
        df = pd.read_excel(sciezka_do_pliku)
        print("--- Podgląd tabeli z Excela ---")
        print(df)
        print("-------------------------------\n")
        
        lista_uczniow = []
        print("Przetwarzanie wierszy:")
        
        for index, row in df.iterrows():
            numer_albumu = row['numer']
            
            imie_ucznia = row['imie'] if 'imie' in df.columns else row['Unnamed: 1']
            
            print(f"Wiersz {index + 1}: Znaleziono ucznia o numerze: {numer_albumu}")
            
            uczen_temp = uczen(name=imie_ucznia, number=numer_albumu)
            lista_uczniow.append(uczen_temp)
            
        return lista_uczniow

    except FileNotFoundError:
        print(f"Błąd: Nie znaleziono pliku o ścieżce: {sciezka_do_pliku}")
    except KeyError as e:
        print(f"Błąd: W pliku Excel brakuje kolumny: {e}")
    except Exception as e:
        print(f"Wystąpił nieoczekiwany błąd: {e}")

if __name__ == "__main__":
    uczeniowie = wczytaj_uczniow("students_list.xlsx")
    
    nadaj_grupy_w(uczeniowie)
    for plik_grup in ("grupy_l.xlsx", "grupy_cs.xlsx", "grupy_lk.xlsx", "grupy_lek.xlsx"):
        nadaj_grupy_z_arkusza(uczeniowie, plik_grup)
    print("\n--- Po nadaniu grup ---")
    if uczeniowie:
        for i, u in enumerate(uczeniowie):
            print(f"Uczeń {i + 1}: Imię: {u.name}, Numer: {u.number}, Grupy: {u.grupy}")
    print("zapis do bazy danych")
    save_to_django(uczeniowie)
